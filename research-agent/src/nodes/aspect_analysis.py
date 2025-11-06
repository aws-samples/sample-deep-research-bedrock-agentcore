"""Stage 2: Aspect Analysis Node

This node identifies specific aspects within each dimension.
Executed in PARALLEL for each dimension (using Send API).
Uses simple LLM call with structured output (NOT a ReAct agent).
"""

import time
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langsmith import traceable

from src.state import AspectAnalysisState, StructuredAspect
from src.config.llm_config import get_llm_for_node
from src.catalog.tool_loader import get_tool_manager
from src.utils.error_handler import handle_node_error
from src.nodes.reference_preparation import get_reference_context_prompt
from src.utils.cancellation import check_cancellation
from src.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)


class StructuredAspectModel(BaseModel):
    """Single aspect with research guidance"""
    name: str = Field(description="Name of the aspect (concise, 3-8 words)")
    reasoning: str = Field(description="Why this aspect is important and what to focus on (2-3 sentences)")
    key_questions: List[str] = Field(description="2-3 specific research questions to investigate")


class Aspects(BaseModel):
    """Structured output for aspects with research guidance"""
    aspects: List[StructuredAspectModel] = Field(
        description="Key aspects with research guidance",
        min_length=1,
        max_length=10  # Will be validated against target in code
    )


ASPECTS_SYSTEM_PROMPT = """You are a research assistant analyzing a dimension of a research topic.

{research_context}

{reference_context}

TOPIC: {topic}

TARGET: Identify up to {target_aspects} specific aspects to investigate within a given dimension.

OUTPUT FORMAT: For EACH aspect, provide:
1. **Name**: Concise name (3-8 words)
2. **Reasoning**: Why this aspect matters and what to focus on (2-3 sentences)
3. **Key Questions**: 2-3 specific research questions to guide investigation

Example:
```json
{{
  "name": "Climate Migration Patterns and Scale",
  "reasoning": "Understanding migration flows is crucial as climate change forces populations to relocate. This examines the scale, destinations, and demographics of climate-driven displacement, which informs policy and resource allocation.",
  "key_questions": [
    "What are the projected migration flows by region through 2050?",
    "Which populations are most vulnerable to climate displacement?",
    "What patterns distinguish climate migration from other migration types?"
  ]
}}
```

IMPORTANT: Return at most {target_aspects} aspects. If you return more, extras will be automatically discarded.
"""

ASPECTS_USER_PROMPT = """Analyze the following dimension and identify key aspects to investigate.

DIMENSION: {dimension}

{search_context}

Return up to {target_aspects} aspects with detailed research guidance that together provide comprehensive coverage of this dimension.
"""


@traceable(name="aspect_analysis_node")
@handle_node_error("aspect_analysis", fallback_return={"original_aspects_by_dimension": {}})
async def aspect_analysis_node(state: AspectAnalysisState) -> Dict[str, Any]:
    """
    Stage 2: Identify specific aspects within a dimension.

    This node is executed in PARALLEL for each dimension.

    Process:
    1. Receive dimension and topic from state
    2. Search for dimension-specific information
    3. Use LLM to identify 3 key aspects

    Args:
        state: AspectAnalysisState with dimension and topic

    Returns:
        Dict with aspects_by_dimension for this dimension
    """
    from src.utils.status_updater import get_status_updater

    # Check if research is cancelled before starting
    check_cancellation(state)

    dimension = state["dimension"]
    topic = state["topic"]
    reference_materials = state.get("reference_materials", [])
    research_session_id = state.get("research_session_id")

    # Get research config
    from src.config.research_config import ResearchConfig
    research_config_dict = state.get("research_config", {})
    if isinstance(research_config_dict, dict):
        research_config = ResearchConfig.from_dict(research_config_dict)
    else:
        research_config = research_config_dict

    target_aspects = research_config.target_aspects_per_dimension if hasattr(research_config, 'target_aspects_per_dimension') else 3

    logger.info(f"Analyzing dimension: {dimension} (target: {target_aspects} aspects)")

    start_time = time.time()

    # Load Gateway tools for search
    manager = get_tool_manager()
    await manager.initialize()

    if not hasattr(research_config, 'research_type'):
        raise ValueError("research_config.research_type is required - config object invalid")

    research_type = research_config.research_type
    logger.info(f"Loading tools for research_type: {research_type}")
    all_tools = await manager.get_tools(research_type, force_refresh=False)

    # Find search tool (prefer ddg_search or brave_search)
    search_tool = None
    for tool in all_tools:
        if tool.name in ['ddg_search', 'brave_search', 'tavily___ddg_search', 'tavily___brave_search']:
            search_tool = tool
            break

    # Perform dimension-specific search using Gateway tool
    search_query = f"{dimension} in {topic}"
    search_results = []

    if search_tool:
        try:
            result = await search_tool.ainvoke({"query": search_query, "max_results": 3})
            # Parse result - Gateway tools return JSON string
            import json
            if isinstance(result, str):
                parsed = json.loads(result)
            else:
                parsed = result

            # Extract results array from Lambda response format
            # Lambda returns: {"query": "...", "results_count": N, "results": [...]}
            if isinstance(parsed, dict) and 'results' in parsed:
                search_results = parsed['results']
            elif isinstance(parsed, list):
                search_results = parsed
            else:
                search_results = []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            search_results = []

    # Format search context
    search_context = ""
    if search_results:
        formatted_results = []
        for item in search_results:
            title = item.get("title", "No title")
            snippet = item.get("snippet", item.get("description", "No snippet"))
            formatted_results.append(f"- {title}: {snippet}")

        search_context = "\n\nRelevant findings:\n" + "\n".join(formatted_results)

    # Get reference context
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

Consider this context when identifying aspects.
"""

    # Get LLM for aspect analysis
    llm = get_llm_for_node("aspect_analysis", state)

    # Prepare system and user prompts
    system_prompt = ASPECTS_SYSTEM_PROMPT.format(
        topic=topic,
        target_aspects=target_aspects,
        research_context=research_context_prompt,
        reference_context=reference_context
    )

    user_prompt = ASPECTS_USER_PROMPT.format(
        dimension=dimension,
        target_aspects=target_aspects,
        search_context=search_context
    )

    # Check if model supports prompt caching
    model_name = getattr(llm, 'model_id', getattr(llm, 'model', ''))
    supports_caching = any(
        model in model_name for model in [
            'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
            'us.anthropic.claude-sonnet-4-20250514-v1:0',
            'us.amazon.nova-pro-v1:0',
            'anthropic.claude-3-5-haiku-20241022-v1:0'
        ]
    )

    logger.info(f"Invoking LLM for {dimension} (model: {model_name}, supports_caching: {supports_caching}, method: simple JSON)")

    try:
        import json
        from langchain_core.messages import SystemMessage, HumanMessage

        # Add JSON format instruction to system prompt
        json_system_prompt = system_prompt + f"""

================================================================================
OUTPUT FORMAT (CRITICAL - READ CAREFULLY)
================================================================================

You MUST respond with ONLY a valid JSON object. No explanations, no markdown, just JSON.

Required structure:
{{
  "aspects": [
    {{
      "name": "Short descriptive name (3-8 words)",
      "reasoning": "Why this matters (2-3 sentences)",
      "key_questions": ["Question 1?", "Question 2?", "Question 3?"]
    }}
  ]
}}

Requirements:
- Return exactly {target_aspects} aspect(s) in the "aspects" array
- Each aspect MUST have: "name", "reasoning", "key_questions"
- "key_questions" must be an array with 2-3 questions
- Do NOT add any text outside the JSON object
- Do NOT wrap in markdown code blocks

Example output:
{{"aspects": [{{"name": "Revenue Growth Analysis", "reasoning": "Understanding revenue trends is critical for valuation. This examines growth rates and sustainability.", "key_questions": ["What is the YoY revenue growth?", "Which segments drive growth?", "Are growth rates sustainable?"]}}]}}"""

        if supports_caching:
            # System message with cache point
            cached_system_message = SystemMessage(
                content=[
                    {"text": json_system_prompt},
                    {"cachePoint": {"type": "default"}}
                ]
            )

            messages = [
                cached_system_message,
                HumanMessage(content=user_prompt)
            ]
        else:
            messages = [
                SystemMessage(content=json_system_prompt),
                HumanMessage(content=user_prompt)
            ]

        logger.info(f"[{dimension}] Step 1/3: Calling Bedrock API WITHOUT toolConfig (simple text response)...")

        # Simple invoke without tools - should be faster and more reliable
        logger.info(f"[{dimension}] Step 2/3: Waiting for Bedrock response...")
        raw_response = llm.invoke(messages)

        logger.info(f"[{dimension}] Step 3/3: Parsing JSON response...")

        # Use robust JSON parser utility
        response_text = raw_response.content.strip()
        response_data = parse_llm_json(
            response_text,
            context=f"{dimension} aspect analysis",
            auto_fix_common_errors=True,
            strict=False
        )

        # Defense 3: Validate structure
        if not isinstance(response_data, dict):
            raise ValueError(f"Response is not a JSON object: {type(response_data)}")

        if "aspects" not in response_data:
            raise ValueError(f"Missing 'aspects' key in response. Keys: {list(response_data.keys())}")

        if not isinstance(response_data["aspects"], list):
            raise ValueError(f"'aspects' is not a list: {type(response_data['aspects'])}")

        # Defense 4: Clean and validate each aspect
        cleaned_aspects = []
        for i, aspect in enumerate(response_data["aspects"]):
            if not isinstance(aspect, dict):
                logger.warning(f"[{dimension}] Aspect {i} is not a dict, skipping: {aspect}")
                continue

            # Ensure required fields exist
            cleaned_aspect = {
                "name": aspect.get("name", f"Unnamed Aspect {i+1}"),
                "reasoning": aspect.get("reasoning", "No reasoning provided"),
                "key_questions": aspect.get("key_questions", [])
            }

            # Defense 5: Fix key_questions if it's not a list
            if isinstance(cleaned_aspect["key_questions"], str):
                # Split by newline or comma
                cleaned_aspect["key_questions"] = [
                    q.strip() for q in cleaned_aspect["key_questions"].replace("\n", ",").split(",")
                    if q.strip()
                ]

            if not isinstance(cleaned_aspect["key_questions"], list):
                cleaned_aspect["key_questions"] = []

            # Ensure at least 1 question
            if len(cleaned_aspect["key_questions"]) == 0:
                cleaned_aspect["key_questions"] = [f"What are the key insights about {cleaned_aspect['name']}?"]

            cleaned_aspects.append(cleaned_aspect)

        if len(cleaned_aspects) == 0:
            raise ValueError(f"No valid aspects found in response")

        # Replace with cleaned data
        response_data["aspects"] = cleaned_aspects

        # Validate with pydantic
        try:
            response = Aspects(**response_data)
        except Exception as e:
            logger.error(f"[{dimension}] Pydantic validation failed: {e}")
            logger.error(f"[{dimension}] Cleaned data: {json.dumps(response_data, indent=2)}")
            raise ValueError(f"Pydantic validation failed: {e}")

        logger.info(f"[{dimension}] ✓ Parsed {len(response.aspects)} aspect(s) successfully")
    except Exception as e:
        logger.error(f"[{dimension}] LLM invoke failed after {time.time() - start_time:.1f}s: {type(e).__name__}: {e}")
        # Re-raise to trigger error handler
        raise

    aspects_list = response.aspects

    # Enforce target count - truncate or warn if mismatch
    if len(aspects_list) > target_aspects:
        logger.warning(f"LLM returned {len(aspects_list)} aspects for {dimension}, truncating to {target_aspects}")
        aspects_list = aspects_list[:target_aspects]
    elif len(aspects_list) < target_aspects:
        logger.warning(f"LLM returned only {len(aspects_list)} aspects for {dimension} (target: {target_aspects})")

    # Convert pydantic models to TypedDict format
    structured_aspects = [
        {
            "name": aspect.name,
            "reasoning": aspect.reasoning,
            "key_questions": aspect.key_questions,
            "completed": False  # Initially all aspects need research
        }
        for aspect in aspects_list
    ]

    elapsed = time.time() - start_time
    logger.info(f"Aspect analysis completed for {dimension} in {elapsed:.2f}s - {len(structured_aspects)} aspects identified")

    # Accumulate results in status updater (thread-safe for parallel execution)
    status_updater = get_status_updater(research_session_id)
    if status_updater:
        # Update stage to show progress (first aspect_analysis will set this)
        status_updater.update_stage('aspect_analysis')
        status_updater.add_dimension(dimension)
        for aspect in structured_aspects:
            status_updater.add_aspect(dimension, aspect)

    # Return in format that matches ResearchState reducer
    # Store in original_aspects_by_dimension (will be refined by research_planning)
    return {
        "original_aspects_by_dimension": {
            dimension: structured_aspects
        }
    }
