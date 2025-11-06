"""
AgentCore Runtime Handler for Chat Agent
Receives requests from BFF via AgentCore Runtime
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from .agent import create_chat_agent
from .config import config

logger = logging.getLogger(__name__)

# Initialize AgentCore app
app = BedrockAgentCoreApp()


@app.entrypoint
async def chat_agent(payload: Dict[str, Any]):
    """
    Chat Agent entrypoint for AgentCore Runtime with streaming support

    Expected payload format:
    {
        "user_id": "user-123",
        "session_id": "chat-456",
        "message": "What are the key findings?",
        "model_id": "us.amazon.nova-pro-v1:0",  # optional
        "research_session_id": "research-789",   # optional
        "research_context": { ... }              # optional research context structure
    }

    Yields:
        str: Streaming response chunks from the Strands agent
    """
    logger.info("📥 Received chat request")
    logger.info(f"Payload type: {type(payload)}")
    logger.info(f"Payload content: {json.dumps(payload, default=str)[:200]}...")

    try:
        # Parse request
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        message = payload.get("message")
        model_id = payload.get("model_id")
        research_session_id = payload.get("research_session_id")
        research_context = payload.get("research_context")

        # Validate required fields
        if not user_id or not session_id or not message:
            error_msg = "Missing required fields: user_id, session_id, message"
            logger.error(f"❌ {error_msg}")
            # AgentCore Runtime will automatically convert dict to JSON
            yield {
                "type": "error",
                "error": error_msg,
                "statusCode": 400
            }
            return

        logger.info(f"Processing: user={user_id}, session={session_id}, research={research_session_id}")
        if research_context:
            dim_count = research_context.get('dimension_count', 0)
            aspect_count = research_context.get('total_aspects', 0)
            logger.info(f"Research context: {dim_count} dimensions, {aspect_count} aspects")
        logger.info(f"Message: {message}")

        # Research context is now passed in the system prompt, not wrapping each message
        # This keeps the user message clean in memory and display
        if research_context:
            topic = research_context.get('topic', 'Unknown Research')
            logger.info(f"Research context available: {topic}")

        # Create Strands agent with AgentCore Memory STM and research tools
        agent = create_chat_agent(
            user_id,
            session_id,
            model_id,
            research_session_id=research_session_id,
            research_context=research_context
        )

        logger.info(f"📨 Sending message to Strands agent (session: {session_id})")
        logger.info(f"💾 Session manager will automatically save messages to AgentCore Memory")

        # Stream response from Strands agent in real-time
        # The session manager automatically handles memory (load history, save exchange)
        # Research context is in system prompt, so we send the user message as-is
        full_response = ""
        tool_calls = []  # Track tool usage
        stream = agent.stream_async(message)

        async for chunk in stream:
            # Debug: Log chunk structure
            logger.debug(f"🔍 Chunk type: {type(chunk)}")
            if isinstance(chunk, dict):
                logger.debug(f"🔍 Chunk keys: {chunk.keys()}")
            else:
                logger.debug(f"🔍 Chunk attributes: {dir(chunk)}")

            # Extract text from chunk
            # Chunk can be: dict with 'delta' key, or object with delta attribute
            text_content = ""

            if isinstance(chunk, dict):
                # Handle dict format
                if 'delta' in chunk and isinstance(chunk['delta'], dict):
                    text_content = chunk['delta'].get('text', '')
                elif 'event' in chunk and isinstance(chunk['event'], dict):
                    event = chunk['event']

                    # Handle nested event format
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta'].get('delta', {})
                        text_content = delta.get('text', '')

                    # Capture tool use events
                    elif 'contentBlockStart' in event:
                        start = event['contentBlockStart']
                        if 'start' in start and 'toolUse' in start['start']:
                            tool_use = start['start']['toolUse']
                            tool_name = tool_use.get('name', 'Unknown')
                            tool_id = tool_use.get('toolUseId', '')

                            # Send tool start event
                            yield {
                                "type": "tool_start",
                                "tool_id": tool_id,
                                "tool_name": tool_name,
                                "input": tool_use.get('input', {})
                            }

                            tool_calls.append({
                                "id": tool_id,
                                "name": tool_name,
                                "input": tool_use.get('input', {}),
                                "status": "running"
                            })

                    # Capture tool result events
                    elif 'messageStop' in event:
                        # Sometimes tool results come at message end
                        pass
            elif hasattr(chunk, 'delta'):
                # Handle object format
                if isinstance(chunk.delta, dict):
                    text_content = chunk.delta.get('text', '')
                elif hasattr(chunk.delta, 'text'):
                    text_content = chunk.delta.text

            # Check for tool use in chunk attributes
            if hasattr(chunk, 'tool_use'):
                tool_use = chunk.tool_use
                tool_name = getattr(tool_use, 'name', 'Unknown')
                tool_id = getattr(tool_use, 'id', '')

                yield {
                    "type": "tool_start",
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "input": getattr(tool_use, 'input', {})
                }

                tool_calls.append({
                    "id": tool_id,
                    "name": tool_name,
                    "input": getattr(tool_use, 'input', {}),
                    "status": "running"
                })

            if text_content:
                full_response += text_content
                # Yield chunk immediately for real-time streaming
                # AgentCore Runtime will automatically convert dict to JSON
                yield {
                    "type": "chunk",
                    "chunk": text_content
                }

        logger.info(f"✅ Response generated successfully")
        logger.info(f"Response length: {len(full_response)} chars")
        if tool_calls:
            logger.info(f"🔧 Used {len(tool_calls)} tools")
        logger.info(f"💾 Messages have been saved to AgentCore Memory by session manager")

        # Send final completion event with metadata
        # AgentCore Runtime will automatically convert dict to JSON
        yield {
            "type": "done",
            "session_id": session_id,
            "response": full_response,
            "model": model_id or config.model_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_calls": tool_calls  # Include tool usage information
        }

    except Exception as e:
        logger.error(f"❌ Error processing chat request: {e}", exc_info=True)
        # AgentCore Runtime will automatically convert dict to JSON
        yield {
            "type": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "statusCode": 500
        }


# Run the app when executed as module
if __name__ == "__main__":
    print("="*80)
    print("💬 Chat Agent for Research Q&A - AgentCore Runtime")
    print("="*80)
    print("✅ Chat Agent ready for deployment")
    print("="*80)
    print("🚀 Starting AgentCore Runtime server...")
    print("="*80)

    # Run the AgentCore app
    app.run()
