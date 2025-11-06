"""ArXiv research tools for ReAct agent"""

import json
from typing import Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_community.utilities.arxiv import ArxivAPIWrapper


# Define input schemas
class ArxivSearchInput(BaseModel):
    """Input schema for ArXiv search"""
    query: str = Field(..., description="Search query for ArXiv papers")


class ArxivSummaryInput(BaseModel):
    """Input schema for ArXiv paper summary"""
    paper_ids: str = Field(
        ...,
        description="ArXiv paper ID or comma-separated IDs (e.g., '2308.08155' or '2308.08155,2401.12345,2309.11111')"
    )


class ArxivSearchTool(BaseTool):
    """Tool for searching ArXiv papers"""

    name: str = "arxiv_search"
    description: str = """Search for scientific papers on ArXiv. Returns up to 5 results with comprehensive metadata:
- Title, authors, publication date
- Paper ID for reference
- FULL ABSTRACT (complete summary of the paper)

IMPORTANT: The abstract is usually sufficient for research purposes. Only use arxiv_get_paper if you need the full paper content (methods, experiments, detailed results).

Best for: physics, mathematics, computer science, AI/ML research."""
    args_schema: Type[BaseModel] = ArxivSearchInput

    def _run(self, query: str) -> str:
        max_results = 5
        """Execute ArXiv search"""
        wrapper = ArxivAPIWrapper(top_k_results=max_results, load_all_available_meta=True)

        try:
            docs = wrapper.get_summaries_as_docs(query)
            results = []

            for i, doc in enumerate(docs):
                meta = doc.metadata
                entry_id = meta.get("Entry ID", "")
                paper_id = entry_id.split("/")[-1] if entry_id else "Unknown ID"

                # Return FULL abstract (not truncated)
                results.append({
                    "index": i + 1,
                    "title": meta.get("Title", ""),
                    "authors": meta.get("Authors", ""),
                    "published": str(meta.get("Published", "")),
                    "paper_id": paper_id,
                    "abstract": doc.page_content  # Full abstract, no truncation
                })

            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": f"ArXiv search failed: {str(e)}"})


class ArxivSummaryTool(BaseTool):
    """Tool for getting detailed ArXiv paper content"""

    name: str = "arxiv_get_paper"
    description: str = """Get FULL paper content from ArXiv (methods, experiments, detailed results).

IMPORTANT:
- arxiv_search already provides complete abstracts
- Only use this tool if you need the full paper text
- This returns up to 5000 characters of paper content
- Use sparingly to avoid context bloat

Supports batch: '2308.08155,2401.12345,2309.11111'"""
    args_schema: Type[BaseModel] = ArxivSummaryInput

    def _run(self, paper_ids: str) -> str:
        """Get detailed paper content (supports batch)"""
        # Parse comma-separated IDs
        id_list = [pid.strip() for pid in paper_ids.split(",")]

        results = []
        wrapper = ArxivAPIWrapper(load_all_available_meta=True, doc_content_chars_max=50000)

        for paper_id in id_list:
            try:
                # Clean paper ID
                if "/" in paper_id:
                    paper_id = paper_id.split("/")[-1]

                documents = wrapper.load(paper_id)

                if not documents:
                    results.append({
                        "paper_id": paper_id,
                        "error": f"No paper found with ID {paper_id}"
                    })
                    continue

                doc = documents[0]
                meta = doc.metadata

                results.append({
                    "paper_id": paper_id,
                    "title": meta.get("Title", ""),
                    "authors": meta.get("Authors", ""),
                    "published": str(meta.get("Published", "")),
                    "summary": meta.get("Summary", ""),
                    "content_preview": doc.page_content[:5000] + "..." if len(doc.page_content) > 5000 else doc.page_content
                })

            except Exception as e:
                results.append({
                    "paper_id": paper_id,
                    "error": f"Failed to get paper: {str(e)}"
                })

        return json.dumps({
            "papers_retrieved": len(results),
            "papers": results
        }, indent=2)


# Create tool instances
arxiv_search_tool = ArxivSearchTool()
arxiv_summary_tool = ArxivSummaryTool()

# Tool list for agent
ARXIV_TOOLS = [arxiv_search_tool, arxiv_summary_tool]
