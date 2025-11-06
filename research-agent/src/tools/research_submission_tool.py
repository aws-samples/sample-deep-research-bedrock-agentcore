"""Research Result Submission Tool

This tool allows research agents to submit their structured findings.
The agent must organize research results with proper sections and citations
before submitting through this tool.
"""

from typing import TypedDict, Optional, ClassVar
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool


class ResearchResultInput(BaseModel):
    """Input schema for research result submission"""
    aspect_key: str = Field(
        description="Unique identifier for this research aspect (format: 'Dimension::AspectName')"
    )
    title: str = Field(
        description="Research aspect title"
    )
    summary: str = Field(
        description="Executive summary of key findings (2-3 paragraphs, 150-300 words)"
    )
    main_content: str = Field(
        description="""Main research content in Markdown format with the following sections:

        ## Introduction
        Brief context and scope

        ## Key Findings
        Main discoveries and insights with evidence

        ## Detailed Analysis
        In-depth analysis addressing research questions

        ## Sources and Citations
        All sources used with proper citations

        Use [Author, Year, Source] format for citations.
        Example: [Smith et al., 2024, arXiv:2401.12345]
        """
    )
    key_sources: list[str] = Field(
        description="List of primary sources cited (titles or IDs)",
        default_factory=list
    )


# Global storage for results (outside the class to avoid Pydantic field issues)
_submitted_results = {}


class SubmitResearchResultTool(BaseTool):
    """Tool for submitting structured research results"""

    name: str = "submit_research_result"
    description: str = """Submit your completed research findings in a structured format.

    Use this tool when you have finished researching and synthesizing information from multiple sources.
    You MUST organize your findings into:
    1. Title: Clear aspect name
    2. Summary: Executive summary of key findings (150-300 words)
    3. Main Content: Full analysis in Markdown format with sections:
       - Introduction
       - Key Findings
       - Detailed Analysis
       - Sources and Citations
    4. Key Sources: List of primary sources used

    This ensures your research is properly structured for the final report.
    Call this tool ONCE at the end of your research with comprehensive findings.
    """
    args_schema: type[BaseModel] = ResearchResultInput

    def _run(
        self,
        aspect_key: str,
        title: str,
        summary: str,
        main_content: str,
        key_sources: list[str]
    ) -> str:
        """Store the structured research result"""
        global _submitted_results

        # Validate inputs
        if not aspect_key or not title or not summary or not main_content:
            return "ERROR: All fields (aspect_key, title, summary, main_content) are required."

        # Store structured result
        result = {
            "aspect_key": aspect_key,
            "title": title,
            "summary": summary,
            "main_content": main_content,
            "key_sources": key_sources,
            "word_count": len(main_content.split())
        }

        # Save to global storage
        _submitted_results[aspect_key] = result

        return f"""✅ Research result submitted successfully!

Aspect: {title}
Summary: {len(summary.split())} words
Main Content: {len(main_content.split())} words
Citations: {len(key_sources)} primary sources

Your structured research has been saved and will be included in the final report."""


def get_submitted_results():
    """Get all submitted results"""
    return _submitted_results


def clear_submitted_results():
    """Clear all submitted results (useful for testing)"""
    global _submitted_results
    _submitted_results = {}


# Create singleton instance
submit_research_result_tool = SubmitResearchResultTool()
