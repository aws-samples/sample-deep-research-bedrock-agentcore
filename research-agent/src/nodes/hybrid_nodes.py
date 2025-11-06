"""Hybrid mode nodes - Real LLM with mock search tools

These nodes use real LLM calls but mock search APIs for fast testing.
"""

import time
from typing import Dict, Any
from langsmith import traceable

from src.state import ResearchState, AspectResearchState
from src.config.llm_config import get_llm_for_node
from src.config.hybrid_config import build_hybrid_research_tools, get_hybrid_search_results
from src.nodes.reference_preparation import get_reference_context_prompt

# Import real nodes to wrap
from src.nodes.topic_analysis import DIMENSIONS_PROMPT, Dimensions
from src.nodes.aspect_analysis import ASPECTS_PROMPT, Aspects
from src.nodes.research_planning import (
    research_planning_node as real_research_planning_node
)
from src.nodes.dimension_reduction import (
    DIMENSION_REDUCER_SYSTEM_PROMPT,
    format_research_summary
)


@traceable(name="hybrid_topic_analysis_node")
def hybrid_topic_analysis_node(state: ResearchState) -> Dict[str, Any]:
    """
    Hybrid topic analysis - Real LLM with mock search results.
    """
    print("\n" + "="*80)
    print("HYBRID MODE: TOPIC ANALYSIS (Real LLM + Mock Search)")
    print("="*80)

    start_time = time.time()

    topic = state.get("topic")
    if not topic:
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

    target_dimensions = getattr(research_config, 'target_dimensions', 3)

    print(f"\n📋 Topic: {topic[:100]}...")
    print(f"📊 Target structure: {target_dimensions} dimensions")

    # Use mock search results
    print("\n🔍 Using mock search results...")
    search_results = get_hybrid_search_results(f"research on {topic}", max_results=5)

    # Format search context
    search_context = "\n\nRelevant information from web:\n"
    search_context += "\n".join([
        f"- [Web] {item['title']}: {item['snippet']}"
        for item in search_results
    ])

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

    # Use real LLM for dimension analysis
    llm = get_llm_for_node("topic_analysis")

    print("\n🤖 Analyzing dimensions with real LLM...")
    prompt = DIMENSIONS_PROMPT.format(
        topic=topic,
        target_dimensions=target_dimensions,
        research_context=research_context_prompt,
        search_context=search_context,
        reference_context=reference_context
    )

    structured_llm = llm.with_structured_output(Dimensions)
    response = structured_llm.invoke(prompt)

    dimensions = response.dimensions

    # Enforce target count
    if len(dimensions) > target_dimensions:
        print(f"   ⚠ LLM returned {len(dimensions)} dimensions, truncating to {target_dimensions}")
        dimensions = dimensions[:target_dimensions]
    elif len(dimensions) < target_dimensions:
        print(f"   ⚠ LLM returned only {len(dimensions)} dimensions (target: {target_dimensions})")

    elapsed = time.time() - start_time

    print(f"\n✅ Identified {len(dimensions)} dimensions in {elapsed:.2f}s:")
    for idx, dim in enumerate(dimensions, 1):
        print(f"   {idx}. {dim}")

    return {
        "dimensions": dimensions,
        "search_results": search_results,
        "workflow_start_time": state.get("workflow_start_time", start_time)
    }


@traceable(name="hybrid_aspect_analysis_node")
def hybrid_aspect_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hybrid aspect analysis - Real LLM with mock search results.
    """
    dimension = state["dimension"]
    topic = state["topic"]
    reference_materials = state.get("reference_materials", [])

    # Get research config
    from src.config.research_config import ResearchConfig
    research_config_dict = state.get("research_config", {})
    if isinstance(research_config_dict, dict):
        research_config = ResearchConfig.from_dict(research_config_dict)
    else:
        research_config = research_config_dict

    target_aspects = getattr(research_config, 'target_aspects_per_dimension', 3)

    print(f"\n🔹 Hybrid analyzing dimension: {dimension}")
    print(f"   Target: {target_aspects} aspects (Real LLM + Mock Search)")

    start_time = time.time()

    # Use mock search results
    search_query = f"{dimension} in {topic}"
    search_results = get_hybrid_search_results(search_query, max_results=3)

    # Format search context
    search_context = "\n\nRelevant findings:\n"
    search_context += "\n".join([
        f"- {item['title']}: {item['snippet']}"
        for item in search_results
    ])

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

    # Use real LLM for aspect analysis
    llm = get_llm_for_node("aspect_analysis")

    prompt = ASPECTS_PROMPT.format(
        topic=topic,
        dimension=dimension,
        target_aspects=target_aspects,
        research_context=research_context_prompt,
        search_context=search_context,
        reference_context=reference_context
    )

    structured_llm = llm.with_structured_output(Aspects)
    response = structured_llm.invoke(prompt)

    aspects_list = response.aspects

    # Enforce target count
    if len(aspects_list) > target_aspects:
        print(f"   ⚠ LLM returned {len(aspects_list)} aspects, truncating to {target_aspects}")
        aspects_list = aspects_list[:target_aspects]
    elif len(aspects_list) < target_aspects:
        print(f"   ⚠ LLM returned only {len(aspects_list)} aspects (target: {target_aspects})")

    # Convert to dict format
    structured_aspects = [
        {
            "name": aspect.name,
            "reasoning": aspect.reasoning,
            "key_questions": aspect.key_questions,
            "completed": False
        }
        for aspect in aspects_list
    ]

    elapsed = time.time() - start_time

    print(f"   ✓ Found {len(structured_aspects)} structured aspects in {elapsed:.2f}s")
    for aspect in structured_aspects:
        print(f"      - {aspect['name']}")

    return {
        "aspects_by_dimension": {
            dimension: structured_aspects
        }
    }


@traceable(name="hybrid_research_agent_node")
def hybrid_research_agent_node(state: AspectResearchState) -> Dict[str, Any]:
    """
    Hybrid research agent - Real LLM ReAct agent with mock search tools.
    """
    aspect = state["aspect"]
    dimension = state["dimension"]
    topic = state["topic"]
    reference_materials = state.get("reference_materials", [])

    aspect_name = aspect["name"]
    aspect_reasoning = aspect["reasoning"]
    aspect_questions = aspect["key_questions"]

    # Get research config
    research_config_dict = state.get("research_config")
    if not research_config_dict:
        raise ValueError("research_config missing from state - this is a critical error")

    from src.config.research_config import ResearchConfig
    try:
        research_config = ResearchConfig.from_dict(research_config_dict)
    except ValueError as e:
        raise ValueError(f"Invalid research_config in state: {e}") from e

    print(f"\n🔬 Hybrid researching: {aspect_name} ({dimension})")
    print(f"   Mode: Real LLM + Mock Tools")

    start_time = time.time()

    # Get research agent with MOCK tools
    from langgraph.prebuilt import create_react_agent
    from langgraph.checkpoint.memory import MemorySaver
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import SystemMessage

    llm = get_llm_for_node("research_agent")

    # Build MOCK tools instead of real ones
    tools = build_hybrid_research_tools(research_config)

    if not tools:
        raise ValueError("No research tools enabled in configuration")

    # System prompt (same as real agent)
    system_prompt = """You are a scientific research assistant specializing in literature review and information synthesis.

Your task is to find and analyze relevant information, then submit structured research results.

RESEARCH STRATEGY:

Use a phased approach to research efficiently:

**PHASE 1 - EXPLORATORY (Round 1):**
- Use exploratory search tools in parallel (arxiv_search, ddg_search, wikipedia_search, etc.)
- Cast a wide net to understand the landscape
- Gather abstracts, summaries, and overview information
- Each tool returns up to 5 results with sufficient detail

**PHASE 2 - DEEP DIVE (Round 2, selective):**
- Based on Phase 1 findings, identify the 2-3 most promising sources
- Use deep-dive tools selectively (arxiv_get_paper, tavily_extract, wikipedia_get_article)
- Only retrieve full content when abstracts/summaries are insufficient
- Call these tools in parallel if multiple sources are needed

**PHASE 3 - SYNTHESIS & OUTPUT (Round 3):**
- Synthesize all gathered information
- Output your complete research findings directly (no tool call needed)

CITATION FORMAT:
- For ArXiv papers: [Author(s), Year, arXiv:ID]
- For web sources: [Title, URL]

CONTENT STRUCTURE:
Write a comprehensive research report in Markdown format with:

## Executive Summary
Brief overview (150-250 words)

## Introduction
Background and context

## Key Findings
Main discoveries with evidence

## Detailed Analysis
In-depth examination

## Conclusions
Summary of insights

## References
List all sources

IMPORTANT:
- Write comprehensive content (800-1500 words)
- Include specific details and examples
- Cite sources throughout
- Output ONLY the markdown content
"""

    # Create ReAct agent with mock tools
    checkpointer = MemorySaver()

    system_message = SystemMessage(content=system_prompt)
    custom_prompt = ChatPromptTemplate.from_messages([
        system_message,
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
    ])

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=custom_prompt,
        checkpointer=checkpointer
    )

    # Get reference context
    reference_context = get_reference_context_prompt(reference_materials)

    # Get research context
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

    # Formulate research query
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
"""

    # Execute agent with mock tools
    thread_id = f"{dimension}::{aspect_name}".replace(" ", "_").replace("/", "_")

    try:
        result = agent.invoke(
            {"messages": [("user", query)]},
            config={"configurable": {"thread_id": thread_id}}
        )

        elapsed = time.time() - start_time

        # Extract final message
        final_message = result["messages"][-1].content if result.get("messages") else ""

        structured_result = {
            "aspect_key": aspect_key,
            "title": aspect_name,
            "content": final_message.strip(),
            "word_count": len(final_message.split())
        }

        print(f"   ✓ Research completed in {elapsed:.2f}s")
        print(f"      Content: {structured_result['word_count']} words")

        return {
            "research_by_aspect": {
                aspect_key: structured_result
            }
        }

    except Exception as e:
        print(f"   ✗ Research failed: {e}")

        return {
            "research_by_aspect": {
                aspect_key: {
                    "aspect_key": aspect_key,
                    "title": aspect_name,
                    "content": f"## Error\n\nResearch failed for {aspect_name}: {str(e)}",
                    "word_count": 0
                }
            }
        }


@traceable(name="hybrid_dimension_reduction_node")
def hybrid_dimension_reduction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hybrid dimension reduction - Real LLM with mock data.
    """
    dimension = state.get("dimension", "Unknown Dimension")
    topic = state.get("topic", "Research Topic")
    aspects_by_dimension = state.get("aspects_by_dimension", {})
    research_by_aspect = state.get("research_by_aspect", {})

    print(f"\n📝 Hybrid synthesizing dimension: {dimension}")
    print(f"   Mode: Real LLM")

    start_time = time.time()

    # Get aspects for this dimension
    aspects = aspects_by_dimension.get(dimension, [])
    aspect_count = len(aspects)

    # Build research summary
    research_summary = format_research_summary(aspects, research_by_aspect, dimension)

    # Build system prompt
    system_prompt = DIMENSION_REDUCER_SYSTEM_PROMPT.format(
        dimension=dimension,
        aspect_count=aspect_count,
        research_summary=research_summary,
        topic=topic
    )

    # Get LLM
    llm = get_llm_for_node("research_agent")

    # Execute LLM directly
    from langchain_core.messages import SystemMessage, HumanMessage

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Synthesize the research materials into a comprehensive section for the dimension "{dimension}".

Output ONLY the markdown content following the structure specified in the system prompt.""")
    ]

    result = llm.invoke(messages)
    markdown_content = result.content if hasattr(result, 'content') else str(result)

    elapsed = time.time() - start_time

    # Save markdown to file
    from src.utils.workspace import get_workspace
    workspace = get_workspace()

    safe_dimension = dimension.replace(" ", "_").replace("/", "_").lower()
    md_filename = workspace.get_dimension_document_path(f"{safe_dimension}.md")

    # Remove .docx extension if get_dimension_document_path added it
    if md_filename.endswith('.md.docx'):
        md_filename = md_filename[:-5]  # Remove .docx, keep .md

    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"   ✓ Section completed in {elapsed:.2f}s")
    print(f"      Words: {len(markdown_content.split())}")
    print(f"      File: {md_filename}")

    return {
        "dimension_documents": {
            dimension: md_filename
        }
    }
