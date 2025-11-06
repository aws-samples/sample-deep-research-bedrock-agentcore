"""Stage 1: Topic Analysis Node

This node performs initial topic analysis to identify key research dimensions.
Uses simple LLM call with structured output (NOT a ReAct agent).
"""

import time
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langsmith import traceable

from src.state import ResearchState
from src.config.llm_config import get_llm_for_node
from src.nodes.reference_preparation import get_reference_context_prompt
from src.utils.cancellation import check_cancellation
from src.catalog.tool_loader import get_tool_manager
import json

logger = logging.getLogger(__name__)


class Dimensions(BaseModel):
    """Structured output for dimensions"""
    dimensions: List[str] = Field(
        description="Key dimensions of the research topic",
        min_length=1,
        max_length=10  # Will be validated against target in code
    )


DIMENSIONS_PROMPT = """You are a research assistant analyzing a complex topic.

Your task: Identify the {target_dimensions} most important dimensions (major aspects/categories) to investigate for this topic.

{research_context}

{reference_context}

For example:
- Topic: "Climate change impact on society"
  Dimensions: ["Environmental Impact", "Economic Consequences", "Social Effects"]

- Topic: "Data Quality in RAG Systems"
  Dimensions: ["Content Classification", "Quality Metrics", "Human-in-the-Loop Workflows"]

Topic to analyze:
{topic}

{search_context}

Return up to {target_dimensions} key dimensions that would provide comprehensive coverage of this topic.
Each dimension should be a distinct aspect that can be researched independently.

IMPORTANT:
- Return at most {target_dimensions} dimensions. If you return more, extras will be automatically discarded.
- You MUST respond in JSON format with the following structure:
{{"dimensions": ["Dimension 1", "Dimension 2"]}}
"""


@traceable(name="topic_analysis_node")
async def topic_analysis_node(state: ResearchState) -> Dict[str, Any]:
    """
    Stage 1: Analyze topic and identify key research dimensions.

    Process:
    1. Extract topic from state
    2. Perform web search for context
    3. Use LLM with structured output to identify dimensions

    Args:
        state: Current research state

    Returns:
        Updated state with dimensions and search results
    """
    from src.utils.status_updater import get_status_updater

    # Check if research is cancelled before starting
    check_cancellation(state)

    start_time = time.time()

    # Update status
    research_session_id = state.get("research_session_id")
    status_updater = get_status_updater(research_session_id)
    if status_updater:
        status_updater.update_stage('topic_analysis')

    # Extract topic and config
    topic = state.get("topic")
    if not topic:
        logger.error("No topic provided")
        return {
            "error": "No topic provided",
        }

    # Get research config
    from src.config.research_config import ResearchConfig
    research_config_dict = state.get("research_config", {})
    if isinstance(research_config_dict, dict):
        research_config = ResearchConfig.from_dict(research_config_dict)
    else:
        research_config = research_config_dict

    target_dimensions = research_config.target_dimensions if hasattr(research_config, 'target_dimensions') else 3

    logger.info(f"STAGE 1: TOPIC ANALYSIS - Topic: {topic[:100]}, Target dimensions: {target_dimensions}")

    from langgraph.prebuilt import create_react_agent

    # Load Gateway tools for exploration
    manager = get_tool_manager()
    await manager.initialize()

    # Get research type from config
    if not hasattr(research_config, 'research_type'):
        raise ValueError("research_config.research_type is required - config object invalid")

    research_type = research_config.research_type
    logger.info(f"Loading tools for research_type: {research_type}")
    all_tools = await manager.get_tools(research_type, force_refresh=False)

    # Filter only search tools needed for exploration (wikipedia and web search)
    exploration_tools = [t for t in all_tools if t.name in ['wikipedia_search', 'ddg_search', 'tavily___wikipedia_search', 'tavily___ddg_search']]

    logger.info(f"Loaded {len(exploration_tools)} exploration tools from Gateway")

    # Create simple agent for topic exploration
    exploration_llm = get_llm_for_node("topic_analysis", state)

    exploration_prompt = f"""Understand this research topic and gather basic background information: "{topic}"

Your task:
1. Identify 2-3 key concepts or terms from this topic
2. Search for general information on these concepts (use broader, well-known terms if specific searches fail)
3. After gathering enough context (2-3 searches maximum), summarize what you learned

IMPORTANT:
- Stop searching after 2-3 tool calls - don't try to find every possible detail
- If a search returns no results, try one broader search term and move on
- Provide a brief summary with the information you found, even if incomplete
- You don't need perfect coverage - just understand the general topic area

Keep it simple - just understand the core research areas, not detailed analysis."""

    logger.info(f"[DEBUG] Creating exploration_agent for topic_analysis - session: {research_session_id}")

    exploration_agent = create_react_agent(
        model=exploration_llm,
        tools=exploration_tools,
    )

    logger.info(f"[DEBUG] Invoking exploration_agent - session: {research_session_id}")

    # Invoke with high recursion limit to prevent premature termination
    exploration_result = await exploration_agent.ainvoke(
        {"messages": [("user", exploration_prompt)]},
        config={
            "recursion_limit": 100,  # High limit to ensure agent can complete exploration
            "configurable": {
                "thread_id": f"topic_exploration_{research_session_id}"
            }
        }
    )

    logger.info(f"[DEBUG] Exploration_agent ainvoke completed - session: {research_session_id}")

    # Extract final message as context
    messages = exploration_result.get("messages", [])
    if messages:
        # Get the last AIMessage content
        final_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        search_context = f"\n\nBackground context:\n{final_message}"
        logger.info(f"[DEBUG] Extracted {len(messages)} messages from exploration_agent")
    else:
        logger.error(f"[DEBUG] No messages returned from exploration_agent - session: {research_session_id}")
        raise ValueError("No messages returned from exploration agent")

    # Get reference context if provided
    reference_materials = state.get("reference_materials", [])
    reference_context = get_reference_context_prompt(reference_materials)

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

Consider this context when identifying dimensions.
"""

    # Get LLM for topic analysis
    llm = get_llm_for_node("topic_analysis", state)

    # Use structured output to extract dimensions
    prompt = DIMENSIONS_PROMPT.format(
        topic=topic,
        target_dimensions=target_dimensions,
        research_context=research_context_prompt,
        search_context=search_context,
        reference_context=reference_context
    )

    # Use simple JSON response instead of structured output (toolConfig)
    # This avoids boto3 timeout issues with toolConfig in Bedrock Converse API

    # Import re for JSON extraction (json already imported at module level)
    import re

    logger.info(f"[DEBUG] Calling LLM invoke for topic_analysis - session: {research_session_id}")

    llm_start = time.time()
    try:
        logger.info(f"[DEBUG] Entering llm.invoke() call - session: {research_session_id}, timestamp: {llm_start}")
        raw_response = llm.invoke(prompt)
        llm_elapsed = time.time() - llm_start
        logger.info(f"[DEBUG] LLM invoke returned successfully - session: {research_session_id}, elapsed: {llm_elapsed:.2f}s")
        logger.info(f"[DEBUG] Response type: {type(raw_response)}, has content: {hasattr(raw_response, 'content')}")
    except Exception as e:
        llm_elapsed = time.time() - llm_start
        logger.error(f"[DEBUG] LLM invoke failed - session: {research_session_id}, elapsed: {llm_elapsed:.2f}s, error type: {type(e).__name__}, error: {e}")
        raise

    response_text = raw_response.content
    logger.info(f"[DEBUG] Response content extracted, length: {len(response_text)} chars")

    # Parse JSON from response
    # Try to extract JSON from markdown code blocks if present
    if "```json" in response_text:
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
    elif "```" in response_text:
        json_match = re.search(r'```\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)

    # Parse JSON
    try:
        response_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}")
        logger.error(f"Raw response: {response_text[:500]}")
        # Fallback: try to find JSON object in the text
        json_match = re.search(r'\{.*"dimensions".*\}', response_text, re.DOTALL)
        if json_match:
            try:
                response_data = json.loads(json_match.group(0))
            except:
                raise ValueError(f"Could not parse dimensions from response: {response_text[:200]}")
        else:
            raise ValueError(f"Could not find JSON in response: {response_text[:200]}")

    # Validate and create Dimensions object
    response = Dimensions(**response_data)
    dimensions = response.dimensions

    # Enforce target count - truncate or warn if mismatch
    if len(dimensions) > target_dimensions:
        logger.warning(f"LLM returned {len(dimensions)} dimensions, truncating to {target_dimensions}")
        dimensions = dimensions[:target_dimensions]
    elif len(dimensions) < target_dimensions:
        logger.warning(f"LLM returned only {len(dimensions)} dimensions (target: {target_dimensions})")

    elapsed = time.time() - start_time
    logger.info(f"Topic analysis completed - {len(dimensions)} dimensions identified in {elapsed:.2f}s: {', '.join(dimensions)}")

    # Update status with dimensions
    if status_updater:
        status_updater.update_progress(
            dimensions=dimensions,
            dimension_count=len(dimensions)
        )

    return {
        "dimensions": dimensions,
        "workflow_start_time": state.get("workflow_start_time", start_time)
    }
