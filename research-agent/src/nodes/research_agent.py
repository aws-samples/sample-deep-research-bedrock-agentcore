"""Stage 3: Research Agent Node

This node performs deep research on each aspect using a ReAct agent.
Executed in PARALLEL for each aspect (using Send API).
Uses LangGraph's create_react_agent with dynamically configured tools.
"""

import os
import time
import json
import logging
import re
from typing import Dict, Any, Optional, List
from langsmith import traceable
from langgraph.prebuilt import create_react_agent

from src.state import AspectResearchState
from src.config.llm_config import get_llm_for_node
from src.config.research_config import ResearchConfig, ResearchToolType
from src.utils.error_handler import handle_node_error
from src.utils.cancellation import ResearchCancelledException, check_cancellation

logger = logging.getLogger(__name__)
from langchain_core.messages import AIMessage, HumanMessage
from src.nodes.reference_preparation import get_reference_context_prompt

# Gateway tool integration
from src.catalog.tool_loader import get_tool_manager


# Checkpointer removed - using Event Tracker instead for AgentCore Memory storage


def create_cache_point_hook(supports_caching: bool = False):
    """
    Create a pre-model hook that adds cache points to conversation history.

    This hook runs BEFORE every LLM call in the ReAct loop.

    Args:
        supports_caching: Whether the model supports prompt caching

    Returns:
        Pre-model hook function
    """
    def hook(state):
        """
        Pre-model hook that adds cache points.
        """
        from langchain_core.messages import ToolMessage

        # Skip for models that don't support caching (to avoid AccessDeniedException)
        if not supports_caching:
            return {}  # No cache points for non-caching models

        messages = state.get("messages", [])

        if not messages:
            return {}

        # Find the last Human or AI message (skip Tool messages)
        target_index = -1
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg, (HumanMessage, AIMessage)):
                target_index = i
                break

        if target_index == -1:
            return {"llm_input_messages": messages}

        target_message = messages[target_index]

        # Check if cache point already exists
        if isinstance(target_message.content, list):
            has_cache_point = any(
                isinstance(item, dict) and "cachePoint" in item
                for item in target_message.content
            )
            if has_cache_point:
                return {"llm_input_messages": messages}

        # Create new content with cache point
        if isinstance(target_message.content, list):
            new_content = target_message.content + [{"cachePoint": {"type": "default"}}]
        elif isinstance(target_message.content, str):
            new_content = [
                {"text": target_message.content},
                {"cachePoint": {"type": "default"}}
            ]
        else:
            # Unknown format, return as-is
            return {"llm_input_messages": messages}

        # Create NEW message with cache point (preserve all attributes)
        if isinstance(target_message, HumanMessage):
            new_message = HumanMessage(content=new_content, **target_message.dict(exclude={"content", "type"}))
        elif isinstance(target_message, AIMessage):
            new_message = AIMessage(content=new_content, **target_message.dict(exclude={"content", "type"}))
        else:
            return {"llm_input_messages": messages}

        # Return new messages with cache point added
        new_messages = messages[:target_index] + [new_message] + messages[target_index + 1:]

        return {"llm_input_messages": new_messages}

    return hook




def parse_research_output(output: str, aspect_key: str, aspect_name: str) -> Dict[str, Any]:
    """
    Parse research agent output to extract structured result.

    Args:
        output: Agent's final output text (markdown content)
        aspect_key: Aspect key to use
        aspect_name: Aspect name to use

    Returns:
        Structured result dict
    """
    content = output.strip()

    result = {
        "aspect_key": aspect_key,
        "title": aspect_name,
        "content": content,
        "word_count": len(content.split())
    }

    return result


async def build_research_tools(config: ResearchConfig) -> List:
    """
    Build list of research tools from Gateway based on research type.

    Uses catalog-based tool loader to fetch tools from AgentCore Gateway
    instead of using local tool implementations.

    Args:
        config: ResearchConfig specifying research type and configuration

    Returns:
        List of LangChain tool instances from Gateway
    """
    try:
        # Get research type from config
        research_type = config.research_type

        logger.debug(f"🔧 Loading Gateway tools for research type: {research_type}")

        # Use tool manager to get tools from Gateway
        manager = get_tool_manager()
        await manager.initialize()

        # Load tools for this research type
        tools = await manager.get_tools(research_type, force_refresh=False)

        logger.info(f"✅ Loaded {len(tools)} Gateway tools for {research_type}")

        # Log ALL tool names for debugging (not just first 5)
        if tools:
            tool_names = [tool.name for tool in tools]
            logger.info(f"   Tool names: {tool_names}")
        else:
            logger.warning(f"   ⚠️  No tools loaded for research_type: {research_type}")

        return tools

    except Exception as e:
        logger.error(f"❌ Failed to load Gateway tools: {e}")
        logger.warning("⚠️  Falling back to empty tool list")
        import traceback
        traceback.print_exc()
        return []


# Checkpointer function removed - not needed for MCP tools
# AgentCore Memory storage handled by Event Tracker instead


async def get_research_agent(config: Optional[ResearchConfig] = None):
    """
    Get or create ReAct research agent with configured tools from Gateway.

    Args:
        config: ResearchConfig specifying tools and settings (None = default)

    Returns:
        Compiled ReAct agent with configured tools
    """
    # Config is REQUIRED - no fallback
    if config is None:
        raise ValueError("ResearchConfig is required for get_research_agent()")

    # Get LLM for research - pass config as state to get correct model
    llm = get_llm_for_node("research_agent", {"research_config": config.to_dict()})

    # Base system prompt
    base_prompt = """You are a research assistant specializing in information gathering and analysis.

Your task is to find and analyze relevant information using appropriate tools, then synthesize findings into a structured research report.

RESEARCH APPROACH:

**Phase 1 - Initial Exploration (5-8 tool calls):**
- Survey the topic using available tools
- Select tools based on the research type (see tool descriptions below)
- Gather diverse perspectives and sources

**Phase 2 - Focused Investigation (Optional, 3-5 tool calls):**
- Follow up on promising leads from Phase 1
- Retrieve detailed information as needed
- Fill gaps in understanding

**Phase 3 - Synthesis & Writing:**
- Analyze and synthesize collected information
- Write comprehensive research report
- Generate output even if some questions remain - work with available information

**Efficiency Guidelines:**
- Choose tools that best match your information needs
- Specialized tools often provide more structured data than general search
- Complete exploratory research before deep-diving into specifics
- Avoid repeated cycles between exploration and investigation

SOURCE-AWARE CITATION SYSTEM:

You will receive search results with URLs from your tool searches.
Each source contains information you can use in your analysis.

**CITATION RULES:**

1. **Specific Facts/Numbers**: Cite immediately after the claim with the source URL
   ✅ "Costs increased 40% in 2024 [https://example.com/article1]"
   ✅ "Model caching reduces expenses by 30-50% [https://example.com/article2]"

2. **Synthesized Information**: Cite all relevant source URLs
   ✅ "Multiple approaches exist [https://source1.com] [https://source2.com]"

3. **Extended Discussion**: Cite every 2-3 sentences when discussing one source
   ✅ "The study describes three strategies. First, baseline assessment...
        Second, optimization planning... These align with best practices [https://source1.com]."

4. **Quantitative Data**: ALWAYS cite immediately with URL
   ✅ "35% cost reduction [https://source3.com]"
   ❌ "significant cost reduction" (without citation)

5. **General Background**: Group related sentences, cite at end
   ✅ "GenAI observability is critical for FSI. It enables real-time monitoring
        and cost tracking [https://source1.com] [https://source2.com]."

**USER-PROVIDED REFERENCE CITATIONS:**

If the user provided reference materials (marked with [REF-1], [REF-2], etc. in the context above):
- Cite using the assigned reference ID when using information from those materials
- Example: "According to the provided analysis [REF-1], costs increased by 40%"
- Example: "Multiple studies support this finding [REF-1] [REF-2]"
- Use these citations for foundational concepts, background, or specific insights from user materials
- You can combine user references and tool search citations: "This approach [REF-1] is validated by recent studies [https://example.com]"

**CITATION FORMAT IN TEXT:**
- User references: Use square brackets with IDs: [REF-1], [REF-2]
- Tool search results: Use square brackets with full URLs: [https://...]
- Place citations at natural sentence boundaries
- Multiple sources: separate with spaces [REF-1] [https://url1] [https://url2]
- Extract URLs from tool results (link, url, or arxiv_id fields)

CONTENT STRUCTURE:
Write a comprehensive research report in Markdown format with the following structure:

## Executive Summary
Brief overview with key findings (cite major claims).

## Introduction
Background and context (cite foundational information).

## Key Findings
Main discoveries with detailed evidence and analysis (cite extensively).

## Detailed Analysis
In-depth examination addressing all research questions (cite all claims).

## Conclusions
Summary of insights and implications (cite supporting evidence).

## References
List all sources you cited in your report (OPTIONAL - only if you want to provide additional context):

- Article Title: https://example.com/article
- Smith et al., 2024: https://arxiv.org/abs/2401.12345
- Wikipedia Article: https://en.wikipedia.org/wiki/Artificial_intelligence

Note: This section is optional since URLs are already cited inline in the text.

IMPORTANT - CONTENT DEPTH:
- Write comprehensive, publication-ready content
- Depth should match the complexity and scope of the research questions
- Include specific details, examples, and quantitative data whenever available
- Cite sources throughout the text using the format above
- Focus on thorough coverage rather than hitting a specific word count
- Typical range: 800-2000+ words depending on topic complexity and available information
"""

    # Add config-specific instructions with search result limits
    config_guidance = f"""
SEARCH RESULT LIMITS (for efficiency):
- When calling search tools (arxiv_search, ddg_search, google_web_search, tavily_search, etc.):
  - Recommended max_results: {config.web_search_max_results}
  - This provides sufficient coverage while managing context efficiently
"""

    system_prompt = base_prompt + config_guidance + config.get_system_prompt_addition()

    # Build tools based on config from Gateway
    tools = await build_research_tools(config)

    if not tools:
        raise ValueError("No research tools enabled in configuration")

    # DEBUG: Log tools being passed to ReAct agent
    logger.info(f"🔧 Creating ReAct agent with {len(tools)} tools:")
    for idx, tool in enumerate(tools, 1):
        logger.info(f"   {idx}. {tool.name} - {tool.description[:80]}...")

    # Check if model supports prompt caching
    model_name = getattr(llm, 'model_id', getattr(llm, 'model', ''))
    supports_caching = any(
        model in model_name for model in [
            'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
            'us.anthropic.claude-sonnet-4-20250514-v1:0',
            'us.anthropic.claude-haiku-4-5-20251001-v1:0',
            'anthropic.claude-3-5-haiku-20241022-v1:0'
        ]
    )

    # Create pre-model hook for caching (if supported)
    pre_hook = None
    if supports_caching:
        pre_hook = create_cache_point_hook(supports_caching)

    # Create ReAct agent with prompt caching if supported
    if supports_caching:
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.messages import SystemMessage

        # Create system message with cache point
        cached_system_message = SystemMessage(
            content=[
                {"text": system_prompt},
                {"cachePoint": {"type": "default"}}
            ]
        )

        # Create custom prompt template with cached system message
        custom_prompt = ChatPromptTemplate.from_messages([
            cached_system_message,
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
        ])

        # Create ReAct agent (no checkpointer - incompatible with MCP tools)
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=custom_prompt,
            pre_model_hook=pre_hook if pre_hook else None,
        )
    else:
        # Create ReAct agent without caching
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.messages import SystemMessage

        system_message = SystemMessage(content=system_prompt)

        custom_prompt = ChatPromptTemplate.from_messages([
            system_message,
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
        ])

        # Create ReAct agent (no checkpointer - incompatible with MCP tools)
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=custom_prompt,
            pre_model_hook=pre_hook if pre_hook else None,
        )

    return agent


@traceable(name="research_agent_node")
@handle_node_error("research_agent", fallback_return={"research_by_aspect": {}})
async def research_agent_node(state: AspectResearchState) -> Dict[str, Any]:
    """
    Stage 3: Deep research on a specific aspect using ReAct agent.

    This node is executed in PARALLEL for each aspect with concurrency control.
    Maximum concurrent executions controlled by CONCURRENCY_LIMITS["research"].

    Process:
    1. Acquire semaphore slot (wait if limit reached)
    2. Create or retrieve ReAct agent
    3. Formulate research query
    4. Let agent use tools to research
    5. Extract final research content
    6. Release semaphore slot

    Args:
        state: AspectResearchState with aspect, dimension, topic

    Returns:
        Dict with research_by_aspect for this aspect
    """
    from src.utils.concurrency import limit_concurrency

    aspect = state["aspect"]  # Now a StructuredAspect dict
    dimension = state["dimension"]
    topic = state["topic"]
    reference_materials = state.get("reference_materials", [])

    # Extract aspect details
    aspect_name = aspect["name"]
    aspect_reasoning = aspect["reasoning"]
    aspect_questions = aspect["key_questions"]

    # Apply concurrency control for research nodes
    async with limit_concurrency("research", aspect_name):
        # All research logic goes inside this context
        return await _execute_research(state, aspect, dimension, topic, reference_materials)


async def _execute_research(state, aspect, dimension, topic, reference_materials):
    """Internal async function to execute research with Gateway tools"""
    from src.utils.status_updater import get_status_updater

    # Check if research is cancelled before starting
    check_cancellation(state)

    aspect_name = aspect["name"]
    aspect_reasoning = aspect["reasoning"]
    aspect_questions = aspect["key_questions"]

    # Get research config from state (REQUIRED - no fallback)
    research_config_dict = state.get("research_config")
    if not research_config_dict:
        error_msg = "research_config missing from state - this is a critical error"
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)

    try:
        research_config = ResearchConfig.from_dict(research_config_dict)
    except ValueError as e:
        error_msg = f"Invalid research_config in state: {e}"
        logger.error(f"❌ {error_msg}")
        logger.error(f"   Config dict: {research_config_dict}")
        raise ValueError(error_msg) from e

    logger.info(f"Researching aspect: {aspect_name} ({dimension}) - Type: {research_config.research_type}, Depth: {research_config.research_depth}")

    # Update stage for frontend (first research will set this)
    research_session_id = state.get("research_session_id")
    status_updater = get_status_updater(research_session_id)
    if status_updater:
        status_updater.update_stage('research')

    start_time = time.time()

    # Get research agent with configured tools from Gateway
    agent = await get_research_agent(config=research_config)

    # Get reference context if available (full mode for detailed research)
    reference_context = get_reference_context_prompt(reference_materials, compressed=False)

    # Get research context if provided
    user_research_context = state.get("research_context", "")
    research_context_prompt = ""
    if user_research_context:
        research_context_prompt = f"""
{'='*80}
📝 RESEARCH CONTEXT
{'='*80}
{user_research_context}
{'='*80}

Keep this context in mind during your research.
"""

    # Create aspect key for submission
    aspect_key = f"{dimension}::{aspect_name}"

    # Get full research structure for context
    aspects_by_dimension = state.get("aspects_by_dimension", {})
    dimensions = list(aspects_by_dimension.keys())

    # Format overall structure context
    structure_context = f"""
{'='*80}
📊 OVERALL RESEARCH STRUCTURE
{'='*80}
This research is organized into {len(dimensions)} dimensions, each with multiple aspects.
Your research will be part of a comprehensive report that synthesizes all findings.

Dimensions (in order):
"""
    for idx, dim in enumerate(dimensions, 1):
        aspects = aspects_by_dimension.get(dim, [])
        structure_context += f"\n{idx}. **{dim}** ({len(aspects)} aspects)"
        if dim == dimension:
            structure_context += " ← YOU ARE HERE"
            for asp_idx, asp in enumerate(aspects, 1):
                asp_name_display = asp.get("name", asp) if isinstance(asp, dict) else asp
                marker = " ← YOUR ASPECT" if asp_name_display == aspect_name else ""
                structure_context += f"\n   {asp_idx}. {asp_name_display}{marker}"

    structure_context += f"""

{'='*80}
💡 RESEARCH CONTEXT GUIDELINES
{'='*80}
- Your research on "{aspect_name}" will be combined with other aspects in "{dimension}"
- Maintain consistency with the overall topic: "{topic}"
- Your findings should complement (not duplicate) other aspects in this dimension
- Write with awareness that this is part of a larger, structured report
- Use appropriate depth and detail for your specific aspect within the broader context
{'='*80}
"""

    # Formulate detailed research query with reasoning and questions
    query = f"""Research the following aspect in depth:

{research_context_prompt}

{reference_context}

{structure_context}

**Topic**: {topic}
**Dimension**: {dimension}
**Aspect**: {aspect_name}
**Aspect Key**: {aspect_key}

**Research Focus**:
{aspect_reasoning}

**Key Research Questions to Address**:
{chr(10).join(f'{i}. {q}' for i, q in enumerate(aspect_questions, 1))}

INSTRUCTIONS:
1. Use search tools to find relevant sources (follow the 3-phase strategy above)
2. Analyze findings across multiple sources
3. Write your comprehensive research report following the CONTENT STRUCTURE specified above
4. Output ONLY the markdown content - no JSON, no wrapper format, just the report itself

CRITICAL - URL EXTRACTION AND CITATION:
As you call tools and receive results, extract URLs from the results:
- From search tools: use 'link' or 'url' field
- From arXiv: construct URL from arxiv_id (https://arxiv.org/abs/ARXIV_ID)
- From Wikipedia: use the 'url' field

When you cite information, include the full URL:
- Specific fact: "Costs increased 40% [https://example.com/article]"
- Synthesis from multiple sources: "Several approaches exist [https://url1] [https://url2]"
- Quantitative data: ALWAYS cite with URL immediately after

Extract and cite URLs consistently throughout your report.
"""

    # Create unique thread ID using research_session_id + aspect
    # This ensures all research in the same session shares the same memory namespace
    # Format: {session_id}_{hash} (using hash to keep under 100 char limit)
    import hashlib

    research_session_id = state.get("research_session_id", "defaultsession")

    # Create a unique identifier for dimension + aspect
    # Use hash to keep thread_id under AWS limit (100 chars)
    aspect_identifier = f"{dimension}::{aspect_name}"
    aspect_hash = hashlib.sha256(aspect_identifier.encode()).hexdigest()[:16]  # First 16 chars of hash

    # Thread ID format: {session_id}_{hash}
    # Example: research_20251008_212353_why_connected_ai_a1b2c3d4e5f6g7h8
    thread_id = f"{research_session_id}_{aspect_hash}"

    # Execute agent
    try:
        # Get user_id from state for proper actor_id
        user_id = state.get("user_id")
        if not user_id:
            logger.warning("⚠️  user_id not found in state - using 'anonymous' for AgentCore Runtime config")
            user_id = "anonymous"

        # Prepare config with thread_id, actor_id, and recursion_limit
        # recursion_limit is a safety net (set higher than expected usage)
        # Primary control is via system prompt instructions
        # Ensure minimum 100 to prevent premature termination
        recursion_limit = max(100, research_config.agent_max_iterations * 2)
        run_config = {
            "configurable": {
                "thread_id": thread_id,
                "actor_id": user_id,  # Use actual user_id from state
                "session_id": research_session_id  # Research session ID
            },
            "recursion_limit": recursion_limit
        }

        try:
            result = await agent.ainvoke(
                {"messages": [("user", query)]},
                config=run_config
            )
        except RecursionError as re:
            logger.error(f"RecursionError for aspect '{aspect_name}' - exceeded limit of {recursion_limit} iterations")
            raise RecursionError(f"Agent exceeded recursion limit ({recursion_limit}) for aspect '{aspect_name}'. Research task too complex.") from re
        except TimeoutError as te:
            logger.error(f"TimeoutError for aspect '{aspect_name}': {te}")
            raise
        except Exception as invoke_error:
            logger.error(f"Error in agent for aspect '{aspect_name}': {invoke_error}")
            raise

        elapsed = time.time() - start_time

        # Debug: Log agent execution details
        messages = result.get("messages", [])
        logger.info(f"🔍 Agent execution completed for {aspect_name}")
        logger.info(f"   Total messages: {len(messages)}")

        # Count tool calls and messages
        tool_call_count = 0
        tool_response_count = 0
        ai_message_count = 0
        tool_names_used = []

        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_call_count += len(msg.tool_calls)
                # Log each tool call name
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    tool_names_used.append(tool_name)
                    logger.info(f"   [{i}] Tool called: {tool_name}")
            elif msg_type == 'ToolMessage':
                tool_response_count += 1
                tool_name = getattr(msg, 'name', 'unknown')
                content_preview = str(msg.content)[:200] if msg.content else "(empty)"
                logger.info(f"   [{i}] ToolMessage ({tool_name}): {content_preview}...")
            elif msg_type == 'AIMessage':
                ai_message_count += 1
                content_preview = str(msg.content)[:100] if msg.content else "(empty)"
                logger.debug(f"   [{i}] AIMessage: {content_preview}...")

        logger.info(f"   Summary: {tool_call_count} tool calls, {tool_response_count} tool responses, {ai_message_count} AI messages")
        if tool_names_used:
            logger.info(f"   🔧 Tools used: {list(set(tool_names_used))}")

        final_message = result["messages"][-1].content if result.get("messages") else ""
        logger.debug(f"   Final message length: {len(final_message)} chars")
        logger.debug(f"   Final message preview: {final_message[:200]}...")

        structured_result = parse_research_output(final_message, aspect_key, aspect_name)

        logger.info(f"Research completed for '{aspect_name}' in {elapsed:.2f}s ({structured_result['word_count']} words)")

        # Log aspect research complete event to AgentCore Memory (FULL CONTENT)
        from src.utils.event_tracker import get_event_tracker

        # Get user_id from state (passed from agent.py via workflow)
        user_id = state.get("user_id")

        event_tracker = get_event_tracker()
        if event_tracker and user_id:
            logger.debug(f"Logging aspect_research_complete to AgentCore Memory: {dimension} / {aspect_name}")
            try:
                event_id = event_tracker.log_aspect_research_complete(
                    session_id=research_session_id,
                    dimension=dimension,
                    aspect=aspect_name,
                    research_content=structured_result,  # Full structured result!
                    citations_count=len(structured_result.get('key_sources', [])),
                    actor_id=user_id  # Pass actual user_id instead of hardcoded "default_user"
                )
                if event_id:
                    logger.debug(f"✅ Event logged successfully: {event_id}")
                else:
                    logger.error(f"❌ Failed to log event (returned None)")
            except Exception as e:
                logger.error(f"❌ Exception while logging event: {e}", exc_info=True)
        elif not user_id:
            logger.warning("⚠️  user_id not found in state - event tracking skipped")
        else:
            logger.warning("⚠️  Event tracker is None, skipping event logging")

        return {
            "research_by_aspect": {
                aspect_key: structured_result
            }
        }

    except ResearchCancelledException as e:
        logger.info(f"Research cancelled by user for aspect '{aspect_name}'")

        # Research was cancelled - return minimal content
        fallback_content = f"""## Research Cancelled

**Note**: This research was cancelled by user.

### Aspect
{aspect_name}

### Status
Research stopped to save tokens. You can restart the research if needed.
"""

        return {
            "research_by_aspect": {
                aspect_key: {
                    "aspect_key": aspect_key,
                    "title": aspect_name,
                    "summary": "Research cancelled by user",
                    "main_content": fallback_content,
                    "key_sources": [],
                    "word_count": len(fallback_content.split())
                }
            }
        }

    except RecursionError as e:
        logger.error(f"RecursionError for aspect '{aspect_name}': {e}")

        # Recursion limit hit - agent made too many tool calls without generating output
        fallback_content = f"""## Research Summary for {aspect_name}

**Note**: Research reached maximum iteration limit before completion.

### Error Details
{str(e)}

### Key Questions
{chr(10).join(f'{i}. {q}' for i, q in enumerate(aspect_questions, 1))}

### Status
This aspect requires manual review or re-execution.
"""

        return {
            "research_by_aspect": {
                aspect_key: {
                    "aspect_key": aspect_key,
                    "title": aspect_name,
                    "summary": "Iteration limit reached",
                    "main_content": fallback_content,
                    "key_sources": [],
                    "word_count": len(fallback_content.split())
                }
            }
        }

    except TimeoutError as e:
        logger.error(f"TimeoutError for aspect '{aspect_name}': {e}")

        fallback_content = f"""## Research Summary for {aspect_name}

**Note**: Research timed out before completion.

### Error Details
{str(e)}

### Key Questions
{chr(10).join(f'{i}. {q}' for i, q in enumerate(aspect_questions, 1))}

### Status
This aspect requires manual review or re-execution with increased timeout.
"""

        return {
            "research_by_aspect": {
                aspect_key: {
                    "aspect_key": aspect_key,
                    "title": aspect_name,
                    "summary": "Research timed out",
                    "main_content": fallback_content,
                    "key_sources": [],
                    "word_count": len(fallback_content.split())
                }
            }
        }

    except Exception as e:
        logger.error(f"Research failed for aspect '{aspect_name}': {type(e).__name__} - {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")

        # Return error in structured format
        return {
            "research_by_aspect": {
                aspect_key: {
                    "aspect_key": aspect_key,
                    "title": aspect_name,
                    "summary": f"Research failed: {str(e)}",
                    "main_content": f"## Error\n\nResearch failed for {aspect_name}: {str(e)}",
                    "key_sources": [],
                    "word_count": 0
                }
            }
        }
