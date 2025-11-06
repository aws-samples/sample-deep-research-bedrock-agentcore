"""Stage 4: Writer Nodes

This module contains nodes for synthesizing research results into a cohesive report.

Flow:
1. write_dimension_section (parallel by dimension) - Synthesize aspect research into cohesive sections
2. generate_executive_summary - Create high-level summary
3. generate_conclusion - Synthesize insights and future directions
4. assemble_final_report - Combine all parts and save to Word document
"""

import time
import json
from typing import Dict, Any, List
from datetime import datetime
from langsmith import traceable

from src.state import ResearchState
from src.config.llm_config import get_llm_for_node
from src.utils.document_writer import (
    create_research_document,
    add_executive_summary,
    add_dimension_section,
    add_references,
    save_document,
    extract_citations_from_markdown,
    add_section_heading,
    parse_markdown_to_word
)


DIMENSION_SYNTHESIS_PROMPT = """You are an expert academic writer creating a cohesive section for a research report.

**Topic**: {topic}
**Dimension**: {dimension}

You have research findings from {aspect_count} related aspects:

{research_contents}

**Your Task:**

Synthesize these findings into a **flowing, cohesive narrative** about {dimension}.

**Requirements:**

1. **Narrative Flow**: Create a unified discussion, not separate aspect summaries
   - Start with foundational concepts, build to advanced topics
   - Show relationships and connections between aspects
   - Avoid subheadings for individual aspects - integrate naturally

2. **Remove Redundancy**:
   - Eliminate duplicate information across aspects
   - Consolidate similar findings
   - Present each key insight only once

3. **Preserve Depth**:
   - Include specific technical details and examples
   - Maintain all important findings from each aspect
   - Keep quantitative data and concrete evidence

4. **Citations**:
   - Maintain all citations in format [Author et al., Year, Source]
   - Ensure citations are accurate and complete
   - Do not create new citations

5. **Structure**:
   - Use ### for conceptual subsections (2-4 subsections recommended)
   - Write 1500-2500 words total
   - Proper markdown formatting

6. **Academic Tone**: Professional, objective, evidence-based

**Output Format:**

Return ONLY the section content in markdown format. Do NOT include:
- The dimension name as a heading (will be added separately)
- Any preamble like "This section discusses..."
- Any meta-commentary

Start directly with content or first subsection (###).
"""


EXECUTIVE_SUMMARY_PROMPT = """You are an expert academic writer creating an executive summary for a research report.

**Topic**: {topic}

**Dimensions Covered**:
{dimensions_list}

**Your Task:**

Write a comprehensive executive summary (300-400 words) that:

1. **Opens with Context**: 1-2 sentences on why this topic matters
2. **Covers All Dimensions**: Highlight 1-2 key findings from each dimension
3. **Shows Connections**: Indicate how dimensions relate or build on each other
4. **Conclusions**: What are the main takeaways across all research?

**Requirements:**

- Professional, accessible language (not overly technical)
- No citations needed (this is high-level)
- No headings or sections
- Start directly with content
- Markdown formatting for emphasis where appropriate

**Output:**

Return ONLY the executive summary text.
"""


CONCLUSION_PROMPT = """You are an expert academic writer creating a conclusion for a research report.

**Topic**: {topic}

**Dimensions Covered**:
{dimensions_list}

**Key Findings Summary**:
{findings_summary}

**Your Task:**

Write a comprehensive conclusion (400-600 words) that:

1. **Synthesis**: Pull together insights across all dimensions
   - What are the overarching themes?
   - How do findings from different dimensions reinforce or complement each other?

2. **Implications**: What do these findings mean?
   - For researchers in this field
   - For practitioners/industry
   - For future development

3. **Future Directions**: Where should research go from here?
   - Identify gaps revealed by this analysis
   - Suggest promising research directions
   - Note emerging trends

4. **Closing**: Brief final thought on the significance of this work

**Requirements:**

- Synthesize, don't just summarize
- Be forward-looking
- Maintain academic tone
- No new citations
- No headings
- Start directly with content
- Markdown formatting where appropriate

**Output:**

Return ONLY the conclusion text.
"""


@traceable(name="write_dimension_section_node")
def write_dimension_section_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize all aspect research for a dimension into one cohesive section.

    This node runs in parallel for each dimension.

    Args:
        state: State containing dimension, aspect research results, topic

    Returns:
        Dict with dimension_sections update
    """
    dimension = state["dimension"]
    topic = state["topic"]
    aspects_by_dimension = state["aspects_by_dimension"]
    research_by_aspect = state["research_by_aspect"]

    print(f"\n📝 Writing section: {dimension}")

    start_time = time.time()

    # Collect all aspect research for this dimension
    aspects = aspects_by_dimension.get(dimension, [])
    research_contents = []

    for aspect in aspects:
        aspect_name = aspect["name"]
        aspect_key = f"{dimension}::{aspect_name}"
        research = research_by_aspect.get(aspect_key, {})

        if isinstance(research, dict):
            research_contents.append({
                "aspect": aspect_name,
                "reasoning": aspect.get("reasoning", ""),
                "summary": research.get("summary", ""),
                "main_content": research.get("main_content", ""),
                "sources": research.get("key_sources", []),
                "word_count": research.get("word_count", 0)
            })

    # Format research contents for LLM
    formatted_research = json.dumps(research_contents, indent=2, ensure_ascii=False)

    # Create synthesis prompt
    prompt = DIMENSION_SYNTHESIS_PROMPT.format(
        topic=topic,
        dimension=dimension,
        aspect_count=len(aspects),
        research_contents=formatted_research
    )

    # Get LLM and synthesize
    llm = get_llm_for_node("aspect_analysis")  # Reuse aspect_analysis LLM config
    response = llm.invoke(prompt)

    section_content = response.content

    elapsed = time.time() - start_time
    word_count = len(section_content.split())

    print(f"   ✓ Section completed in {elapsed:.2f}s")
    print(f"      Words: {word_count}")
    print(f"      Synthesized from {len(aspects)} aspects")

    return {
        "dimension_sections": {
            dimension: section_content
        }
    }


@traceable(name="generate_executive_summary_node")
def generate_executive_summary_node(state: ResearchState) -> Dict[str, Any]:
    """
    Generate executive summary based on all dimension sections.

    Args:
        state: Full research state

    Returns:
        Dict with executive_summary
    """
    print(f"\n📋 Generating executive summary...")

    start_time = time.time()

    topic = state.get("topic", "")
    dimensions = state.get("dimensions", [])

    # Format dimensions list
    dimensions_list = "\n".join(f"{i+1}. {dim}" for i, dim in enumerate(dimensions))

    # Create prompt
    prompt = EXECUTIVE_SUMMARY_PROMPT.format(
        topic=topic,
        dimensions_list=dimensions_list
    )

    # Generate summary
    llm = get_llm_for_node("aspect_analysis")
    response = llm.invoke(prompt)

    executive_summary = response.content

    elapsed = time.time() - start_time
    print(f"   ✓ Executive summary completed in {elapsed:.2f}s")
    print(f"      Words: {len(executive_summary.split())}")

    return {
        "executive_summary": executive_summary,
        "current_stage": "executive_summary_complete"
    }


@traceable(name="generate_conclusion_node")
def generate_conclusion_node(state: ResearchState) -> Dict[str, Any]:
    """
    Generate conclusion synthesizing insights across all dimensions.

    Args:
        state: Full research state

    Returns:
        Dict with conclusion
    """
    print(f"\n📋 Generating conclusion...")

    start_time = time.time()

    topic = state.get("topic", "")
    dimensions = state.get("dimensions", [])
    dimension_sections = state.get("dimension_sections", {})

    # Format dimensions list
    dimensions_list = "\n".join(f"{i+1}. {dim}" for i, dim in enumerate(dimensions))

    # Extract key findings from each section (first paragraph or up to 300 chars)
    findings_summary = []
    for dimension in dimensions:
        section = dimension_sections.get(dimension, "")
        # Get first 300 characters as summary
        summary = section[:300] + "..." if len(section) > 300 else section
        findings_summary.append(f"**{dimension}**: {summary}")

    findings_text = "\n\n".join(findings_summary)

    # Create prompt
    prompt = CONCLUSION_PROMPT.format(
        topic=topic,
        dimensions_list=dimensions_list,
        findings_summary=findings_text
    )

    # Generate conclusion
    llm = get_llm_for_node("aspect_analysis")
    response = llm.invoke(prompt)

    conclusion = response.content

    elapsed = time.time() - start_time
    print(f"   ✓ Conclusion completed in {elapsed:.2f}s")
    print(f"      Words: {len(conclusion.split())}")

    return {
        "conclusion": conclusion,
        "current_stage": "conclusion_complete"
    }


@traceable(name="assemble_final_report_node")
def assemble_final_report_node(state: ResearchState) -> Dict[str, Any]:
    """
    Assemble final report and save as Word document.

    Args:
        state: Full research state with all sections

    Returns:
        Dict with final_report (markdown) and report_file (path)
    """
    print(f"\n📄 Assembling final report...")

    start_time = time.time()

    topic = state.get("topic", "")
    dimensions = state.get("dimensions", [])
    executive_summary = state.get("executive_summary", "")
    dimension_sections = state.get("dimension_sections", {})
    conclusion = state.get("conclusion", "")

    # Create Word document
    doc = create_research_document(f"Research Report: {topic[:100]}")

    # Add executive summary
    add_executive_summary(doc, executive_summary)

    # Collect all citations
    all_citations = set()
    all_citations.update(extract_citations_from_markdown(executive_summary))

    # Add dimension sections
    for dimension in dimensions:
        section_content = dimension_sections.get(dimension, "")

        # Extract citations from section
        section_citations = extract_citations_from_markdown(section_content)
        all_citations.update(section_citations)

        # Add section to document
        add_dimension_section(doc, dimension, section_content)

    # Add conclusion
    add_section_heading(doc, "Conclusion", level=1)
    parse_markdown_to_word(doc, conclusion)
    all_citations.update(extract_citations_from_markdown(conclusion))

    # Add references
    sorted_citations = sorted(list(all_citations))
    if sorted_citations:
        doc.add_page_break()
        add_references(doc, sorted_citations)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_slug = "".join(c if c.isalnum() else "_" for c in topic[:50])
    filename = f"research_report_{topic_slug}_{timestamp}.docx"

    # Save document
    save_document(doc, filename)

    elapsed = time.time() - start_time
    print(f"\n   ✓ Report assembled in {elapsed:.2f}s")
    print(f"      File: {filename}")
    print(f"      Dimensions: {len(dimensions)}")
    print(f"      Citations: {len(sorted_citations)}")

    # Also create markdown version for reference
    markdown_report = f"""# Research Report: {topic}

## Executive Summary

{executive_summary}

"""

    for dimension in dimensions:
        section_content = dimension_sections.get(dimension, "")
        markdown_report += f"\n## {dimension}\n\n{section_content}\n\n"

    markdown_report += f"""## Conclusion

{conclusion}

## References

"""
    for i, citation in enumerate(sorted_citations, 1):
        markdown_report += f"{i}. {citation}\n"

    return {
        "final_report": markdown_report,
        "report_file": filename,
        "current_stage": "report_complete"
    }
