"""Research Planning Node - Unified aspect refinement and reference integration

This node serves as the final preparation stage before research execution.
It handles two scenarios:

1. With references: Integrates reference context with discovered aspects
2. Without references: Performs quality control and refinement of aspects
"""

import time
import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langsmith import traceable

from src.state import ResearchState, StructuredAspect
from src.config.llm_config import get_llm_for_node
from src.nodes.reference_preparation import get_reference_context_prompt
from src.utils.cancellation import check_cancellation

logger = logging.getLogger(__name__)


class RefinedAspect(BaseModel):
    """Refined aspect for research"""
    name: str = Field(description="Aspect name (3-8 words)")
    reasoning: str = Field(description="Why this aspect matters (2-3 sentences)")
    key_questions: List[str] = Field(description="2-3 research questions")

class RefinedAspectsOutput(BaseModel):
    """Simplified refined aspects output"""
    aspects_by_dimension: Dict[str, List[RefinedAspect]] = Field(
        description="Mapping of dimensions to refined aspects"
    )
    summary: str = Field(
        default="Aspects refined successfully",
        description="Brief summary of refinement"
    )


REFINEMENT_ONLY_SYSTEM = """You are a research quality control specialist reviewing a multi-dimensional research plan.

{research_context}

RESEARCH TOPIC: {topic}

TARGET STRUCTURE: {target_dimensions} dimensions × {target_aspects} aspects per dimension = {total_aspects} total aspects

QUALITY CRITERIA:

1. **No Duplicates**: Aspects should not overlap across different dimensions
2. **Balanced Coverage**: Each dimension should have EXACTLY {target_aspects} aspects of similar scope
3. **Topic Alignment**: All aspects must directly relate to the research topic
4. **Mutual Exclusivity**: Within a dimension, aspects should not overlap
5. **Coverage Gaps**: Identify and add missing critical aspects
6. **Appropriate Scope**: Aspects should be researchable but not too narrow/broad

OUTPUT FORMAT: Each aspect must include:
- "name": Concise name (3-8 words)
- "reasoning": Why important and what to focus on (2-3 sentences)
- "key_questions": List of 2-3 specific research questions

STRUCTURE REQUIREMENT: Final output must have EXACTLY {target_dimensions} dimensions with EXACTLY {target_aspects} aspects each.

NOTE: You MAY rename dimensions if needed for clarity, but keep the total count at {target_dimensions}.

RESPONSE FORMAT: You MUST respond in JSON format with this structure:
{{
  "aspects_by_dimension": {{
    "Dimension Name": [
      {{"name": "Aspect Name", "reasoning": "Why important...", "key_questions": ["Q1", "Q2"]}}
    ]
  }},
  "summary": "Brief summary of refinement"
}}
"""

REFINEMENT_ONLY_USER = """Review and refine the following research structure to ensure high-quality coverage.

CURRENT RESEARCH STRUCTURE:
{current_structure}

Analyze the structure and return the refined version with explanations for any changes made.
"""


REFINEMENT_WITH_REFERENCES_SYSTEM = """You are a research planning specialist refining a multi-dimensional research plan.

{research_context}

RESEARCH TOPIC: {topic}

TARGET STRUCTURE: {target_dimensions} dimensions × {target_aspects} aspects per dimension = {total_aspects} total aspects

{reference_context}

Your task: Refine aspects while considering insights from reference materials.

INSTRUCTIONS:

1. **Quality Control**: Apply standard refinement criteria (no duplicates, balanced coverage, etc.)

2. **Structure Requirement**: Final output must have EXACTLY {target_dimensions} dimensions with EXACTLY {target_aspects} aspects each

3. **Reference Integration**: Use reference materials to:
   - Enhance aspect reasoning with specific insights
   - Refine key questions to be more focused and actionable
   - Identify gaps that need additional research
   - Build upon concepts mentioned in references

4. **Format**: Each aspect must include:
   - "name": Concise name (3-8 words)
   - "reasoning": Enhanced with reference insights (2-3 sentences)
   - "key_questions": Refined questions considering reference context (2-3 questions)

NOTE: All aspects will be researched further. References inform planning, not replace research.

RESPONSE FORMAT: You MUST respond in JSON format with this structure:
{{
  "aspects_by_dimension": {{
    "Dimension Name": [
      {{"name": "Aspect Name", "reasoning": "Why important...", "key_questions": ["Q1", "Q2"]}}
    ]
  }},
  "summary": "Brief summary of refinement"
}}
"""

REFINEMENT_WITH_REFERENCES_USER = """Review and refine the following research structure while integrating insights from the reference materials.

DISCOVERED RESEARCH STRUCTURE:
{current_structure}

Analyze the structure, integrate reference insights, determine coverage, and return the refined version with explanations.
"""


@traceable(name="research_planning_node")
async def research_planning_node(state: ResearchState) -> Dict[str, Any]:
    """
    Unified Research Planning: Aspect refinement with optional reference integration.

    This node processes aspects discovered through topic/aspect analysis and:
    - Without references: Performs quality control and refinement
    - With references: Integrates reference insights into aspect guidance

    Args:
        state: ResearchState with aspects_by_dimension and optional reference_materials

    Returns:
        Updated state with refined aspects_by_dimension
    """
    from src.utils.status_updater import get_status_updater

    # Check if research is cancelled before starting
    check_cancellation(state)

    start_time = time.time()

    # Update status to research_planning stage
    research_session_id = state.get("research_session_id")
    status_updater = get_status_updater(research_session_id)
    if status_updater:
        status_updater.update_stage('research_planning')

    # Get current state
    topic = state.get("topic", "")
    # Read from original_aspects_by_dimension (from aspect_analysis)
    aspects_by_dimension = state.get("original_aspects_by_dimension", {})
    reference_materials = state.get("reference_materials", [])
    user_research_context = state.get("research_context", "")

    # Get research config
    from src.config.research_config import ResearchConfig
    research_config_dict = state.get("research_config", {})
    if isinstance(research_config_dict, dict):
        research_config = ResearchConfig.from_dict(research_config_dict)
    else:
        research_config = research_config_dict

    target_dimensions = research_config.target_dimensions if hasattr(research_config, 'target_dimensions') else 3
    target_aspects = research_config.target_aspects_per_dimension if hasattr(research_config, 'target_aspects_per_dimension') else 3
    total_target = target_dimensions * target_aspects

    # Check if we have references
    has_references = bool(reference_materials)
    total_aspects = sum(len(aspects) for aspects in aspects_by_dimension.values())

    mode = "WITH references" if has_references else "without references"
    logger.info(f"STAGE 2.5: RESEARCH PLANNING - {mode} - {len(aspects_by_dimension)} dimensions, {total_aspects} aspects")

    # Format current structure
    current_structure = json.dumps(aspects_by_dimension, indent=2)

    # Get LLM
    llm = get_llm_for_node("research_planning", state)

    # Prepare research context prompt
    research_context_prompt = ""
    if user_research_context:
        research_context_prompt = f"""
{'='*80}
📝 RESEARCH CONTEXT
{'='*80}
{user_research_context}
{'='*80}

Consider this context when refining aspects.
"""

    # Prepare system and user prompts based on mode
    if has_references:
        # Use compressed mode: only key points, not full summaries
        reference_context = get_reference_context_prompt(reference_materials, compressed=True)
        system_prompt = REFINEMENT_WITH_REFERENCES_SYSTEM.format(
            research_context=research_context_prompt,
            topic=topic,
            target_dimensions=target_dimensions,
            target_aspects=target_aspects,
            total_aspects=total_target,
            reference_context=reference_context
        )
        user_prompt = REFINEMENT_WITH_REFERENCES_USER.format(
            current_structure=current_structure
        )
    else:
        system_prompt = REFINEMENT_ONLY_SYSTEM.format(
            research_context=research_context_prompt,
            topic=topic,
            target_dimensions=target_dimensions,
            target_aspects=target_aspects,
            total_aspects=total_target
        )
        user_prompt = REFINEMENT_ONLY_USER.format(
            current_structure=current_structure
        )

    # Use simple JSON response instead of structured output (toolConfig)
    # This avoids boto3 timeout issues with toolConfig in Bedrock Converse API

    # Import at module level (already imported above, but keeping for clarity)
    import re
    from langchain_core.messages import SystemMessage, HumanMessage

    # Retry logic for transient errors
    max_retries = 2
    retry_delay = 5  # seconds

    for attempt in range(max_retries + 1):
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Simple invoke without structured output
            raw_response = await llm.ainvoke(messages)
            response_text = raw_response.content

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
                json_match = re.search(r'\{.*"aspects_by_dimension".*\}', response_text, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group(0))
                else:
                    raise ValueError(f"Could not find JSON in response: {response_text[:200]}")

            # Validate and create RefinedAspectsOutput object
            response = RefinedAspectsOutput(**response_data)
            break  # Success - exit retry loop

        except Exception as e:
            # Check if it's a validation error (structural problem, not transient)
            is_validation_error = "validation error" in str(e).lower() or "field required" in str(e).lower()
            error_str = str(e)
            is_last_attempt = (attempt == max_retries)

            if is_last_attempt:
                logger.error(f"LLM invocation failed after {max_retries + 1} attempts: {type(e).__name__} - {error_str[:100]}")

                # Fallback: use original aspects without refinement
                fallback_aspects = {}
                for dimension, aspects in aspects_by_dimension.items():
                    aspect_dicts = []
                    for aspect in aspects:
                        if isinstance(aspect, dict):
                            aspect_dicts.append({
                                "name": aspect.get("name", str(aspect)),
                                "reasoning": aspect.get("reasoning", ""),
                                "key_questions": aspect.get("key_questions", []),
                                "completed": False
                            })
                        else:
                            aspect_dicts.append({
                                "name": str(aspect),
                                "reasoning": "",
                                "key_questions": [],
                                "completed": False
                            })
                        fallback_aspects[dimension] = aspect_dicts

                return {
                    "aspects_by_dimension": fallback_aspects,
                    "refinement_changes": [f"Error during refinement (after {max_retries + 1} attempts) - using original structure"]
                }
            else:
                # Retry
                print(f"\n⚠️  LLM invocation failed (attempt {attempt + 1}/{max_retries + 1}): {error_str}")
                print(f"   Retrying immediately...")

    refined_aspects_raw = response.aspects_by_dimension
    summary = response.summary

    # Validate response
    if not refined_aspects_raw:
        print(f"\n⚠️  LLM returned empty aspects_by_dimension, using original structure")
        refined_aspects_raw = aspects_by_dimension

    elapsed = time.time() - start_time

    # Convert RefinedAspect models to dict format
    refined_aspects = {}

    for dimension, aspects_list in refined_aspects_raw.items():
        aspect_dicts = []
        for aspect in aspects_list:
            # Convert to dict matching StructuredAspect format
            aspect_dict = {
                "name": aspect.name,
                "reasoning": aspect.reasoning,
                "key_questions": aspect.key_questions,
                "completed": False  # All aspects need research
            }
            aspect_dicts.append(aspect_dict)

        refined_aspects[dimension] = aspect_dicts

    # Extract dimension names from refined aspects
    refined_dimensions = list(refined_aspects.keys())

    # Log completion
    refined_total = sum(len(aspects) for aspects in refined_aspects.values())
    logger.info(f"Research planning completed in {elapsed:.2f}s - {refined_total} total aspects across {len(refined_dimensions)} dimensions")

    # Log dimensions identified event to AgentCore Memory
    research_session_id = state.get("research_session_id")
    if research_session_id:
        from src.utils.event_tracker import get_event_tracker
        user_id = state.get("user_id")
        event_tracker = get_event_tracker()
        if event_tracker and user_id:
            event_tracker.log_dimensions_identified(
                session_id=research_session_id,
                dimensions=refined_dimensions,
                aspects_by_dimension=refined_aspects,
                actor_id=user_id
            )

    return {
        "aspects_by_dimension": refined_aspects,
        "dimensions": refined_dimensions  # Update dimensions list to match refined structure
    }
