"""Stage 4: Dimension Reduction Node

This node synthesizes research from multiple aspects within a dimension
and writes a cohesive markdown document section.

Each dimension reduction runs in parallel, creating independent .md files.
"""

import time
import json
import logging
from typing import Dict, Any
from langsmith import traceable
from langgraph.prebuilt import create_react_agent

from src.state import ResearchState
from src.utils.error_handler import handle_node_error
from src.config.llm_config import get_llm_for_node
from src.tools.word_document_tools import word_document_tools
from src.utils.cancellation import check_cancellation

logger = logging.getLogger(__name__)


DIMENSION_REDUCER_SYSTEM_PROMPT = """You are an expert academic writer creating a comprehensive section for a research report.

{research_context}

**Your Task:**
Write a cohesive, publication-ready section about "{dimension}" by synthesizing research from {aspect_count} related aspects.

**Research Materials:**
{research_summary}

**Content Requirements:**
- **Synthesize**: Create a flowing narrative, not separate aspect summaries
- **Remove Redundancy**: Consolidate duplicate information across aspects
- **Preserve Citations**: Include all citations. Use format:
  - ArXiv papers: [Author et al., Year, arXiv:ID]
  - Web sources: [URL] (NO author, NO year, just URL)
  - Wikipedia: [Article Title, Wikipedia]
- **Logical Flow**: Start with foundational concepts, build to advanced topics
- **Depth & Coverage**:
  - Write comprehensive, cohesive synthesis that fully integrates all aspect findings
  - Include specific details, examples, and quantitative data from the research
  - Depth should match the richness of the research materials and complexity of the dimension
  - Focus on thorough integration rather than hitting a specific word count
  - Typical range: 1,500-3,000+ words depending on dimension complexity and research depth

**Structure:**
Write your synthesis in Markdown format with the following structure:

# {dimension}

## Introduction
Brief overview of this dimension and its importance in the context of "{topic}".

## [Conceptual Section 1]
Create 2-4 conceptual subsections that naturally integrate the aspects.
DO NOT use aspect names as subsection titles - organize by concepts/themes.

## [Conceptual Section 2]
Continue synthesizing across aspects...

## Key Findings and Implications
Summary of main insights and their significance.

**Important:**
- Output ONLY the markdown content
- Do NOT use aspect names as headings - reorganize by concepts
- Integrate findings from multiple aspects into each section
- Include inline citations as you write:
  * ArXiv: [Author et al., Year, arXiv:ID]
  * Web: [URL]
  * Wikipedia: [Article Title, Wikipedia]
- Do NOT generate a References section - it will be consolidated later
- This section will be included directly in the final report
"""


def format_research_summary(aspects: list, research_by_aspect: dict, dimension: str) -> str:
    """
    Format research materials into a compact summary for the prompt.

    Args:
        aspects: List of aspect dicts with name, reasoning, key_questions
        research_by_aspect: Dict of research results keyed by aspect_key
        dimension: Dimension name

    Returns:
        Formatted research summary string
    """
    summary_parts = []

    for i, aspect in enumerate(aspects, 1):
        aspect_name = aspect["name"]
        aspect_key = f"{dimension}::{aspect_name}"
        research = research_by_aspect.get(aspect_key, {})

        if isinstance(research, dict):
            part = f"""
**Aspect {i}: {aspect_name}**
- Why Important: {aspect.get('reasoning', 'N/A')}
- Key Questions: {', '.join(aspect.get('key_questions', []))}
- Word Count: {research.get('word_count', 0)} words

Research Content:
{research.get('content', 'N/A')}

---
"""
            summary_parts.append(part)

    return "\n".join(summary_parts)


@traceable(name="dimension_reduction_node")
@handle_node_error("dimension_reduction", fallback_return={"dimension_documents": {}})
async def dimension_reduction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize aspect research into a cohesive dimension section document.

    This node runs in parallel for each dimension with concurrency control.
    Maximum concurrent executions controlled by CONCURRENCY_LIMITS["dimension_reduction"].
    Creates independent markdown files.

    Args:
        state: State with dimension, aspects, research results

    Returns:
        Dict with dimension_documents mapping dimension to filename
    """
    from src.utils.concurrency import limit_concurrency

    dimension = state["dimension"]
    topic = state.get("topic", "")
    aspects_by_dimension = state["aspects_by_dimension"]
    research_by_aspect = state["research_by_aspect"]
    user_research_context = state.get("research_context", "")
    research_session_id = state.get("research_session_id")

    # Apply concurrency control for dimension reduction nodes
    async with limit_concurrency("dimension_reduction", dimension):
        # All logic goes inside this context
        return await _execute_dimension_reduction(
            state, dimension, topic, aspects_by_dimension, research_by_aspect, user_research_context, research_session_id
        )


async def _execute_dimension_reduction(state, dimension, topic, aspects_by_dimension, research_by_aspect, user_research_context="", research_session_id=None):
    """Internal function to execute dimension reduction with all the logic"""
    import time
    from src.utils.status_updater import get_status_updater

    # Check if research is cancelled before starting
    check_cancellation(state)

    logger.info(f"Writing dimension section: {dimension}")

    # Update stage for frontend (first dimension_reduction will set this)
    status_updater = get_status_updater(research_session_id)
    if status_updater:
        status_updater.update_stage('dimension_reduction')

    start_time = time.time()

    # Get aspects for this dimension
    aspects = aspects_by_dimension.get(dimension, [])

    if not aspects:
        logger.warning(f"No aspects found for dimension: {dimension}")
        return {"dimension_documents": {}}

    # Generate UNIQUE document ID with timestamp to prevent conflicts
    import uuid
    from src.utils.workspace import get_workspace

    workspace = get_workspace()
    timestamp = int(time.time() * 1000)  # milliseconds
    dimension_slug = dimension.lower().replace(' ', '_').replace('/', '_')[:30]
    document_id = f"dim_{dimension_slug}_{timestamp}_{uuid.uuid4().hex[:8]}"
    filename = workspace.get_dimension_document_path(document_id)

    # Format research materials
    research_summary = format_research_summary(aspects, research_by_aspect, dimension)

    # Prepare research context prompt
    research_context_prompt = ""
    if user_research_context:
        research_context_prompt = f"""
{'='*80}
📝 RESEARCH CONTEXT
{'='*80}
{user_research_context}
{'='*80}

Consider this context when synthesizing the dimension section.
"""

    # Create system prompt
    system_prompt = DIMENSION_REDUCER_SYSTEM_PROMPT.format(
        research_context=research_context_prompt,
        dimension=dimension,
        topic=topic,
        aspect_count=len(aspects),
        research_summary=research_summary
    )

    # Get LLM - use simple model without tools
    llm = get_llm_for_node("dimension_reduction", state)

    # Execute LLM with streaming (faster hang detection than invoke)
    # Streaming allows timeout to trigger on first chunk, not after full response
    try:
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Synthesize the research materials into a comprehensive section for the dimension "{dimension}".

Output ONLY the markdown content following the structure specified in the system prompt.""")
        ]

        # Use async streaming for faster hang detection
        # If Bedrock hangs, timeout occurs after 30s (first chunk), not after full response
        stream = llm.astream(messages)

        # Get first chunk - this will timeout quickly if API hangs
        full = await anext(stream)

        # Accumulate remaining chunks
        async for chunk in stream:
            full += chunk

        # Extract text content from AIMessageChunk
        # Content can be: str, list[dict], or other formats
        if hasattr(full, 'content'):
            content = full.content
            if isinstance(content, list):
                # Extract text from list of content blocks
                markdown_content = ""
                for block in content:
                    if isinstance(block, dict) and 'text' in block:
                        markdown_content += block['text']
                    elif isinstance(block, dict) and 'type' in block and block['type'] == 'text':
                        markdown_content += block.get('text', '')
            elif isinstance(content, str):
                markdown_content = content
            else:
                markdown_content = str(content)
        else:
            markdown_content = str(full)

        elapsed = time.time() - start_time

        # Save markdown to file
        md_filename = filename.replace('.docx', '.md')
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        word_count = len(markdown_content.split())
        logger.info(f"Dimension section completed in {elapsed:.2f}s - {word_count} words")

        # Log dimension document complete event to AgentCore Memory (FULL CONTENT)
        research_session_id = state.get("research_session_id")
        if research_session_id:
            from src.utils.event_tracker import get_event_tracker
            user_id = state.get("user_id")

            event_tracker = get_event_tracker()
            if event_tracker and user_id:
                logger.info(f"Logging dimension_document_complete to AgentCore Memory: {dimension}")
                try:
                    event_id = event_tracker.log_dimension_document_complete(
                        session_id=research_session_id,
                        dimension=dimension,
                        markdown_content=markdown_content,  # Full markdown content!
                        word_count=word_count,
                        filename=md_filename,
                        actor_id=user_id
                    )
                    if event_id:
                        logger.info(f"✅ Event logged successfully: {event_id}")
                    else:
                        logger.error(f"❌ Failed to log event (returned None)")
                except Exception as e:
                    logger.error(f"❌ Exception while logging event: {e}", exc_info=True)
            elif not user_id:
                logger.warning("⚠️  user_id not found in state - event tracking skipped")
            else:
                logger.warning("⚠️  Event tracker is None, skipping event logging")

        return {
            "dimension_documents": {
                dimension: md_filename
            }
        }

    except Exception as e:
        logger.error(f"Dimension reduction failed for {dimension}: {e}", exc_info=True)

        return {
            "dimension_documents": {
                dimension: None
            }
        }
