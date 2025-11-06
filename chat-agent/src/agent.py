"""
Chat Agent with Strands + AgentCore Memory STM
"""
import logging
import json
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

from llm_models import LLM_MODELS

from .config import config
from .tools import create_research_tools

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_research_context(research_session_id: str, research_memory_id: str, user_id: str, aws_region: str = 'us-west-2') -> Optional[Dict[str, Any]]:
    """
    Load research context (dimensions/aspects structure) from AgentCore Memory

    Args:
        research_session_id: Research session ID
        research_memory_id: AgentCore Memory ID for research
        user_id: User ID (actor ID used by Research Agent)
        aws_region: AWS region

    Returns:
        Research context dict with topic, dimensions, and aspects, or None if not found
    """
    try:
        logger.info(f"📖 Loading research context from session {research_session_id}")
        logger.info(f"   Using actor ID: {user_id}")

        client = boto3.client('bedrock-agentcore', region_name=aws_region)

        # Load ALL research events at once for in-memory caching (prevents ThrottledException)
        # Use pagination since AWS limits maxResults to 100
        logger.info(f"📦 Loading ALL research events into memory...")
        all_events = []
        next_token = None

        while True:
            params = {
                'memoryId': research_memory_id,
                'sessionId': research_session_id,
                'actorId': user_id,  # Use actual user_id (Research Agent stores with this)
                'includePayloads': True,
                'maxResults': 100  # AWS maximum
            }
            if next_token:
                params['nextToken'] = next_token

            response = client.list_events(**params)

            events = response.get('events', [])
            all_events.extend(events)

            next_token = response.get('nextToken')
            if not next_token:
                break

        logger.info(f"   Loaded {len(all_events)} events into memory")

        # Find dimensions_identified event (NOT research_planning_complete!)
        topic = None
        dimensions_data = None

        for event in all_events:
            try:
                payload = event.get('payload', [])
                if isinstance(payload, list) and len(payload) > 0:
                    blob_data = payload[0].get('blob')
                    if blob_data:
                        data = json.loads(str(blob_data))
                        event_type = data.get('event_type')

                        # Get topic from research_start
                        if event_type == 'research_start':
                            topic = data.get('topic', 'Unknown Research')

                        # Get dimensions from dimensions_identified (correct event!)
                        elif event_type == 'dimensions_identified':
                            dimensions_data = data
                            logger.info(f"✅ Found dimensions_identified event")
                            break
            except Exception as e:
                logger.debug(f"Error parsing event: {e}")
                continue

        if not dimensions_data:
            logger.warning(f"⚠️  No dimensions_identified event found")
            # Still return all_events for defensive tool access
            return {
                'topic': topic or 'Unknown Research',
                'dimensions': [],
                'dimension_count': 0,
                'total_aspects': 0,
                'all_events': all_events  # Cache for tools
            }

        # Extract dimensions and aspects from aspects_by_dimension structure
        dimensions_list = dimensions_data.get('dimensions', [])
        aspects_by_dimension = dimensions_data.get('aspects_by_dimension', {})

        # Build research context structure
        dimensions = []
        for dim_name in dimensions_list:
            aspects = aspects_by_dimension.get(dim_name, [])
            dimensions.append({
                'name': dim_name,
                'aspects': [{'name': asp.get('name'), 'reasoning': asp.get('reasoning')} for asp in aspects]
            })

        research_context = {
            'topic': topic or dimensions_data.get('topic', 'Unknown Research'),
            'dimensions': dimensions,
            'dimension_count': dimensions_data.get('dimension_count', len(dimensions)),
            'total_aspects': dimensions_data.get('total_aspects', sum(len(d['aspects']) for d in dimensions)),
            'all_events': all_events  # Cache all events for tools to use
        }

        logger.info(f"📚 Loaded research context: {research_context['dimension_count']} dimensions, {research_context['total_aspects']} aspects")
        logger.info(f"💾 Cached {len(all_events)} events for tool access (prevents ThrottledException)")
        return research_context

    except ClientError as e:
        logger.error(f"❌ AWS error loading research context: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error loading research context: {e}")
        return None


def create_chat_agent(
    user_id: str,
    session_id: str,
    model_id: Optional[str] = None,
    research_session_id: Optional[str] = None,
    research_context: Optional[Dict[str, Any]] = None
) -> Agent:
    """
    Create a Strands Agent with AgentCore Memory STM Session Manager
    and optional research tools

    Args:
        user_id: Unique user identifier (actorId)
        session_id: Unique session identifier
        model_id: Optional model ID (short name like 'nova_pro' or full Bedrock ID)
        research_session_id: Optional research session to link and access
        research_context: Optional research context structure (dimensions, aspects, etc.)

    Returns:
        Configured Strands Agent with research tools if research_session_id provided
    """
    logger.info(f"Creating chat agent - user: {user_id}, session: {session_id}")

    if research_session_id:
        logger.info(f"🔗 Linking to research session: {research_session_id}")

        # Load research context from AgentCore Memory if not provided
        if not research_context and config.research_memory_id:
            logger.info(f"📖 Research context not provided, loading from memory...")
            research_context = load_research_context(
                research_session_id=research_session_id,
                research_memory_id=config.research_memory_id,
                user_id=user_id,  # Pass actual user_id for actor ID
                aws_region=config.aws_region
            )

        if research_context:
            dim_count = research_context.get('dimension_count', 0)
            aspect_count = research_context.get('total_aspects', 0)
            logger.info(f"📚 Research context: {dim_count} dimensions, {aspect_count} aspects")

    try:
        # Convert short model name to full Bedrock model ID if needed
        if model_id and model_id in LLM_MODELS:
            full_model_id = LLM_MODELS[model_id]
            logger.info(f"🔄 Converted model_id '{model_id}' -> '{full_model_id}'")
        else:
            # Already a full model ID or None (use default)
            full_model_id = model_id or config.model_id

        logger.info(f"🤖 Using model: {full_model_id}")

        # Configure AgentCore Memory for STM with caching
        agentcore_memory_config = AgentCoreMemoryConfig(
            memory_id=config.memory_id,
            session_id=session_id,
            actor_id=user_id,
            # Enable conversation history caching
            enable_prompt_caching=True,
            # STM only - no retrieval config needed for basic conversation continuity
        )

        # Create session manager with STM
        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=agentcore_memory_config,
            region_name=config.aws_region
        )

        # Create BedrockModel with aggressive caching enabled
        # This caches system prompts and conversation history for cost optimization
        bedrock_model = BedrockModel(
            model_id=full_model_id,
            cache_prompt="default",  # Cache system prompt aggressively
        )

        # Build system prompt with research context if available
        system_prompt = config.get_system_prompt(research_context)

        # Create research tools if research session is linked
        tools = None
        if research_session_id and config.research_memory_id:
            logger.info(f"🔧 Creating research tools for session {research_session_id}")

            # Get cached events from research_context (if available)
            cached_events = research_context.get('all_events') if research_context else None

            tools = create_research_tools(
                research_session_id=research_session_id,
                research_memory_id=config.research_memory_id,
                user_id=user_id,  # Pass user_id for actor ID
                cached_events=cached_events,  # Pass cached events to prevent re-querying
                aws_region=config.aws_region
            )
            logger.info(f"✅ Created {len(tools)} research tools")

        # Create Strands Agent with caching-enabled model and tools
        agent = Agent(
            system_prompt=system_prompt,
            session_manager=session_manager,
            model=bedrock_model,
            tools=tools,  # None if no research session
        )

        tool_status = f"with {len(tools)} research tools" if tools else "without tools"
        logger.info(f"✅ Chat agent created successfully {tool_status} and prompt caching enabled")
        return agent

    except Exception as e:
        logger.error(f"❌ Failed to create chat agent: {e}", exc_info=True)
        raise


def handle_chat_message(
    user_id: str,
    session_id: str,
    message: str,
    model_id: Optional[str] = None,
    research_session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle a chat message with conversation continuity via AgentCore Memory STM

    Args:
        user_id: User identifier
        session_id: Chat session identifier
        message: User's message
        model_id: Optional model override
        research_session_id: Optional research context

    Returns:
        Response dictionary with AI response and metadata
    """
    logger.info(f"📨 Processing chat message - user: {user_id}, session: {session_id}")
    logger.debug(f"Message: {message[:100]}...")

    try:
        # Create agent with STM session manager
        agent = create_chat_agent(user_id, session_id, model_id)

        # Get response from agent
        # The session manager automatically:
        # 1. Loads conversation history from AgentCore Memory
        # 2. Adds it to the LLM context
        # 3. Gets AI response
        # 4. Saves the exchange back to AgentCore Memory
        agent_result = agent(message)

        # Extract response text from AgentResult object
        response_text = str(agent_result)

        logger.info(f"✅ Response generated successfully")
        logger.debug(f"Response: {response_text[:100]}...")

        return {
            "session_id": session_id,
            "response": response_text,
            "model": model_id or config.model_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "research_session_id": research_session_id
        }

    except Exception as e:
        logger.error(f"❌ Failed to handle chat message: {e}", exc_info=True)
        raise


# Agent cache for session reuse (optional optimization)
_agent_cache: Dict[str, Agent] = {}

def get_cached_agent(user_id: str, session_id: str, model_id: Optional[str] = None) -> Agent:
    """
    Get or create a cached agent instance for session reuse
    Note: Be careful with caching - session manager tracks session state
    """
    cache_key = f"{user_id}:{session_id}:{model_id or config.model_id}"

    if cache_key not in _agent_cache:
        _agent_cache[cache_key] = create_chat_agent(user_id, session_id, model_id)

    return _agent_cache[cache_key]


def clear_agent_cache(user_id: Optional[str] = None, session_id: Optional[str] = None):
    """Clear agent cache for specific user/session or all"""
    global _agent_cache

    if user_id and session_id:
        keys_to_remove = [k for k in _agent_cache.keys() if k.startswith(f"{user_id}:{session_id}:")]
        for key in keys_to_remove:
            del _agent_cache[key]
    else:
        _agent_cache.clear()

    logger.info(f"🗑️  Agent cache cleared")
