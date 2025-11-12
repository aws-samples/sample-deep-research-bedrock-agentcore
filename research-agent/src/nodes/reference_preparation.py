"""Stage 0: Reference Preparation Node

This node prepares reference materials provided by the user.
Loads content from URLs or ArXiv papers and generates comprehensive summaries.
"""

import json
import logging
from typing import Dict, Any, List
from langsmith import traceable

from src.state import ResearchState, ReferenceMaterial
from src.config.llm_config import get_llm_for_node
from src.catalog.tool_loader import get_tool_manager
from src.utils.cancellation import check_cancellation

logger = logging.getLogger(__name__)


async def load_url_content(url: str, research_type: str = 'basic_web') -> Dict[str, str]:
    """Load URL content using Tavily extract from Gateway"""
    try:
        # Load Gateway tools
        manager = get_tool_manager()
        await manager.initialize()
        all_tools = await manager.get_tools(research_type, force_refresh=False)

        # Find tavily_extract tool
        extract_tool = None
        for tool in all_tools:
            if 'extract' in tool.name.lower() and 'tavily' in tool.name.lower():
                extract_tool = tool
                break

        if not extract_tool:
            logger.warning("tavily_extract tool not found in Gateway")
            return {"title": url, "content": "", "error": "Tool not available"}

        result = await extract_tool.ainvoke({"urls": url})

        # Parse JSON result
        data = json.loads(result)

        if "error" in data:
            return {"title": url, "content": "", "error": data["error"]}

        results = data.get("results", [])
        if results:
            extracted = results[0]
            return {
                "title": url.split('//')[-1].split('/')[0],  # Domain name as fallback
                "content": extracted.get("content", ""),
                "url": extracted.get("url", url)
            }

        return {"title": url, "content": "", "error": "No content extracted"}

    except Exception as e:
        logger.error(f"Error loading URL {url}: {e}")
        return {"title": url, "content": "", "error": str(e)}


def sanitize_pdf_name_for_bedrock(filename: str) -> str:
    """
    Sanitize PDF filename for Bedrock Converse API.

    Rules:
    - Only alphanumeric, whitespace, hyphens, parentheses, square brackets allowed
    - No consecutive whitespace
    - Convert underscores to hyphens
    - Remove file extension
    """
    import re

    # Remove file extension
    if '.' in filename:
        filename = filename.rsplit('.', 1)[0]

    # Convert underscores to hyphens
    sanitized = filename.replace('_', '-')

    # Keep only allowed characters
    sanitized = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '', sanitized)

    # Replace consecutive whitespace with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)

    # Trim whitespace
    sanitized = sanitized.strip()

    return sanitized or "document"


async def generate_pdf_summary_with_bytes(
    pdf_bytes: bytes,
    title: str,
    note: str = "",
    dimensions: List[str] = None,
    research_context: str = "",
    state: dict = None
) -> Dict[str, Any]:
    """Generate comprehensive summary from PDF bytes using Bedrock Converse API.

    Args:
        pdf_bytes: PDF file bytes (max 4.5MB)
        title: PDF filename or title
        note: Optional user note
        dimensions: Research dimensions for context
        research_context: User-provided research context
        state: State dict for model configuration

    Returns:
        Dict with summary and key_points
    """
    import boto3
    import os
    import asyncio

    # Sanitize filename for Bedrock API
    sanitized_name = sanitize_pdf_name_for_bedrock(title)

    # Validate size (4.5MB limit for Bedrock Converse)
    if len(pdf_bytes) > 4.5 * 1024 * 1024:
        return {
            "summary": f"Error: PDF size ({len(pdf_bytes)/1024/1024:.2f} MB) exceeds 4.5MB limit",
            "key_points": []
        }

    # Prepare context prompts
    research_context_prompt = ""
    if research_context:
        research_context_prompt = f"""
{'='*80}
📝 RESEARCH CONTEXT
{'='*80}
{research_context}
{'='*80}

Consider this context when summarizing the reference material.
"""

    dimension_context = ""
    if dimensions:
        dimension_context = f"""RESEARCH DIMENSIONS (for context):
The overall research will explore these dimensions: {', '.join(dimensions)}

When summarizing, pay special attention to insights relevant to these dimensions.
"""

    system_prompt = SUMMARY_SYSTEM_PROMPT.format(
        research_context=research_context_prompt,
        dimension_context=dimension_context
    )

    user_note = f"User Note: {note}" if note else ""

    try:
        # Get model ID from config
        from src.config.llm_config import get_model_id_for_node
        model_id = get_model_id_for_node("reference_prep", state)

        bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-west-2')
        )

        # Use run_in_executor for sync boto3 call
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: bedrock_runtime.converse(
                modelId=model_id,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'document': {
                                    'format': 'pdf',
                                    'name': sanitized_name,
                                    'source': {
                                        'bytes': pdf_bytes
                                    }
                                }
                            },
                            {
                                'text': f"""Analyze the following PDF reference material and create a comprehensive summary.

Title: {title}
Type: PDF
{user_note}

Provide a structured summary following the format specified in the system prompt."""
                            }
                        ]
                    }
                ],
                system=[
                    {'text': system_prompt}
                ]
            )
        )

        # Extract summary from response
        summary_text = response['output']['message']['content'][0]['text']

        # Extract key points
        key_points = extract_key_points_from_summary(summary_text)

        return {
            "summary": summary_text,
            "key_points": key_points
        }

    except Exception as e:
        logger.error(f"Error generating PDF summary: {e}", exc_info=True)
        return {
            "summary": f"Error generating summary: {str(e)}",
            "key_points": []
        }


SUMMARY_SYSTEM_PROMPT = """You are a research analyst summarizing reference materials for a research project.

{research_context}

{dimension_context}

TASK: Analyze reference materials and create comprehensive summaries for research context.

OUTPUT STRUCTURE:
1. **Main Topic**: What is this material about? (1-2 sentences)
2. **Key Concepts**: List 3-5 important terms, ideas, or definitions
3. **Methods/Approaches**: How does it approach the problem? What techniques are used?
4. **Key Findings**: Main results, conclusions, or arguments (3-5 bullet points)
5. **Relevance for Research**: Why this matters and how it can inform future research

Keep the summary comprehensive but concise (500-800 words total).
Format clearly with section headers.
"""

SUMMARY_USER_PROMPT = """Analyze the following reference material and create a comprehensive summary.

Title: {title}
Type: {ref_type}
{user_note}

Content:
{content}

Provide a structured summary following the format specified in the system prompt.
"""


async def generate_comprehensive_summary(
    title: str,
    content: str,
    ref_type: str,
    note: str = "",
    dimensions: List[str] = None,
    research_context: str = "",
    state: dict = None
) -> Dict[str, Any]:
    """Generate comprehensive summary using LLM with research dimension context"""

    llm = get_llm_for_node("reference_prep", state)

    # Truncate content if too long (keep first 15000 chars)
    truncated_content = content[:15000]
    if len(content) > 15000:
        truncated_content += "\n\n[Content truncated for length...]"

    # Add research context if available
    research_context_prompt = ""
    if research_context:
        research_context_prompt = f"""
{'='*80}
📝 RESEARCH CONTEXT
{'='*80}
{research_context}
{'='*80}

Consider this context when summarizing the reference material.
"""

    # Add dimension context if available
    dimension_context = ""
    if dimensions:
        dimension_context = f"""RESEARCH DIMENSIONS (for context):
The overall research will explore these dimensions: {', '.join(dimensions)}

When summarizing, pay special attention to insights relevant to these dimensions.
"""

    # Prepare system and user prompts
    system_prompt = SUMMARY_SYSTEM_PROMPT.format(
        research_context=research_context_prompt,
        dimension_context=dimension_context
    )

    user_note = f"User Note: {note}" if note else ""
    user_prompt = SUMMARY_USER_PROMPT.format(
        title=title,
        ref_type=ref_type.upper(),
        user_note=user_note,
        content=truncated_content
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

    try:
        if supports_caching:
            from langchain_core.messages import SystemMessage, HumanMessage

            # System message with cache point
            cached_system_message = SystemMessage(
                content=[
                    {"text": system_prompt},
                    {"cachePoint": {"type": "default"}}
                ]
            )

            messages = [
                cached_system_message,
                HumanMessage(content=user_prompt)
            ]

            response = await llm.ainvoke(messages)
        else:
            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await llm.ainvoke(messages)
        summary_text = response.content

        # Extract key points (simple extraction from summary)
        key_points = extract_key_points_from_summary(summary_text)

        return {
            "summary": summary_text,
            "key_points": key_points
        }

    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        return {
            "summary": f"Error generating summary: {str(e)}",
            "key_points": []
        }


def extract_key_points_from_summary(summary: str) -> List[str]:
    """Extract key points from summary text"""
    key_points = []

    # Look for bullet points or numbered items
    lines = summary.split('\n')
    for line in lines:
        line = line.strip()
        # Match bullet points (-, *, •) or numbered items
        if line.startswith(('-', '*', '•', '1.', '2.', '3.', '4.', '5.')):
            # Clean up the point
            clean_point = line.lstrip('-*•0123456789. ').strip()
            if clean_point and len(clean_point) > 20:  # Meaningful points
                key_points.append(clean_point)

    # Limit to top 5 points
    return key_points[:5]


def get_reference_context_prompt(materials: List[ReferenceMaterial], compressed: bool = False) -> str:
    """
    Generate prompt section from reference materials with citation IDs.
    This will be prepended to system prompts in subsequent nodes.

    Args:
        materials: List of reference materials
        compressed: If True, only include key points (for research_planning)
                   If False, include full summary (for research agents)
    """
    if not materials:
        return ""

    context = "\n" + "="*80 + "\n"
    context += "📚 REFERENCE MATERIALS PROVIDED\n"
    context += "="*80 + "\n"
    context += "The user has provided the following reference materials as context:\n\n"

    for i, mat in enumerate(materials, 1):
        citation_id = f"REF-{i}"
        context += f"{i}. [{mat['type'].upper()}] {mat['title']} **[{citation_id}]**\n"
        context += f"   Source: {mat['source']}\n"
        if mat.get('note'):
            context += f"   Note: {mat['note']}\n"
        context += "\n"

        if compressed:
            # Compressed mode: Only key points
            context += "   Key Points:\n"
            key_points = mat.get('key_points', [])
            if key_points:
                for point in key_points[:5]:  # Max 5 points
                    context += f"   • {point}\n"
            else:
                # Fallback: extract first 200 chars from summary
                summary_preview = mat['summary'][:200].strip()
                context += f"   • {summary_preview}...\n"
        else:
            # Full mode: Complete summary
            context += "   Summary:\n"
            summary_lines = mat['summary'].split('\n')
            for line in summary_lines:
                context += f"   {line}\n"

        context += "\n"

    context += "="*80 + "\n"
    context += "INSTRUCTIONS: Use these materials as foundational context when:\n"
    context += "- Identifying research dimensions\n"
    context += "- Breaking down aspects\n"
    context += "- Conducting detailed research\n"
    context += "- Synthesizing findings\n"
    if not compressed:
        context += "\nWhen citing information from these materials in your research report:\n"
        context += "- Use the assigned citation ID (e.g., [REF-1], [REF-2])\n"
        context += "- Example: \"According to the provided analysis [REF-1], costs increased by 40%\"\n"
    context += "="*80 + "\n\n"

    return context


@traceable(name="reference_preparation_node")
async def reference_preparation_node(state: ResearchState) -> Dict[str, Any]:
    """
    Stage 0: Prepare reference materials from user-provided sources.

    Process:
    1. Check if reference materials are provided in config
    2. For each reference:
       - Load content (ArXiv or URL)
       - Generate comprehensive summary with LLM
       - Extract key points
    3. Store structured summaries in state
    4. Skip if no references provided

    Args:
        state: ResearchState with research_config containing optional reference_materials

    Returns:
        Dict with reference_materials list (empty if none provided)
    """

    # Check if research is cancelled before starting
    check_cancellation(state)

    logger.info("STAGE 0: Reference Preparation")

    # Update stage for frontend
    from src.utils.status_updater import get_status_updater
    research_session_id = state.get("research_session_id")
    status_updater = get_status_updater(research_session_id)
    if status_updater:
        status_updater.update_stage('reference_preparation')

    # Get reference materials config and dimensions
    config = state.get("research_config", {})
    references_config = config.get("reference_materials", [])
    dimensions = state.get("dimensions", [])
    user_research_context = state.get("research_context", "")

    # Skip if no references provided
    if not references_config:
        logger.info("No reference materials provided - skipping to topic analysis")
        return {"reference_materials": []}

    materials = []

    # Get research type for tool loading
    from src.config.research_config import ResearchConfig
    research_config_dict = state.get("research_config", {})
    if isinstance(research_config_dict, dict):
        research_config = ResearchConfig.from_dict(research_config_dict)
    else:
        research_config = research_config_dict
    if not hasattr(research_config, 'research_type'):
        raise ValueError("research_config.research_type is required - config object invalid")

    research_type = research_config.research_type

    for idx, ref in enumerate(references_config, 1):
        ref_type = ref.get("type")
        note = ref.get("note", "")

        # Load content based on type
        if ref_type == "url":
            url = ref.get("url")
            loaded = await load_url_content(url, research_type)
            source = url

        elif ref_type == "pdf":
            # PDF is provided as base64 string from BFF (for JSON transport)
            pdf_bytes_base64 = ref.get("pdf_bytes_base64")
            title = ref.get("title", ref.get("filename", "Untitled PDF"))

            if not pdf_bytes_base64:
                logger.warning(f"No PDF bytes provided for reference {idx}")
                continue

            # Decode base64 string to bytes for Bedrock Converse API
            import base64
            try:
                pdf_bytes = base64.b64decode(pdf_bytes_base64)
            except Exception as e:
                logger.error(f"Failed to decode PDF base64 for {title}: {e}")
                continue

            # Generate PDF summary directly with bytes
            summary_result = await generate_pdf_summary_with_bytes(
                pdf_bytes=pdf_bytes,
                title=title,
                note=note,
                dimensions=dimensions if dimensions else None,
                research_context=user_research_context,
                state=state
            )

            materials.append({
                "type": "pdf",
                "source": title,  # Use filename as source
                "title": title,
                "summary": summary_result["summary"],
                "key_points": summary_result["key_points"],
                "note": note
            })

            continue

        else:
            logger.warning(f"Unknown reference type: {ref_type}")
            continue

        # Check for loading errors (for arxiv/url only)
        if "error" in loaded or not loaded.get("content"):
            logger.warning(f"Failed to load content: {loaded.get('error', 'No content')}")
            continue

        title = loaded.get("title", "Untitled")
        content = loaded.get("content", "")

        # Generate comprehensive summary with dimension and research context
        summary_result = await generate_comprehensive_summary(
            title=title,
            content=content,
            ref_type=ref_type,
            note=note,
            dimensions=dimensions if dimensions else None,
            research_context=user_research_context,
            state=state
        )

        materials.append({
            "type": ref_type,
            "source": source,
            "title": title,
            "summary": summary_result["summary"],
            "key_points": summary_result["key_points"],
            "note": note
        })

    logger.info(f"Reference preparation completed - {len(materials)} materials prepared")

    # Log references prepared event to AgentCore Memory
    if materials:
        from src.utils.event_tracker import get_event_tracker
        user_id = state.get("user_id")
        event_tracker = get_event_tracker()
        if event_tracker and user_id:
            logger.info(f"Logging references_prepared to AgentCore Memory: {len(materials)} materials")
            try:
                event_id = event_tracker.log_references_prepared(
                    session_id=research_session_id,
                    reference_materials=materials,  # Full list with summaries!
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

    return {"reference_materials": materials}
