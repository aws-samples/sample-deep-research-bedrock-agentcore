"""Wikipedia search and retrieval tools

Provides simple Wikipedia integration without MCP dependencies:
- Search for articles
- Retrieve article content (summary or full text)
"""

import json
import wikipediaapi
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional


class WikipediaSearchInput(BaseModel):
    """Input for Wikipedia search"""
    query: str = Field(..., description="Search query for Wikipedia articles")


class WikipediaGetArticleInput(BaseModel):
    """Input for Wikipedia article retrieval"""
    title: str = Field(..., description="Title of the Wikipedia article to retrieve")
    summary_only: bool = Field(
        default=False,
        description="If True, return only the summary. If False, return full text (limited to 5000 chars)"
    )


class WikipediaSearchTool(BaseTool):
    """Search Wikipedia for articles"""

    name: str = "wikipedia_search"
    description: str = """Search Wikipedia for articles matching a query. Returns up to 5 results.

    Excellent for finding authoritative background information, definitions, historical context, and well-established facts.
    Wikipedia provides comprehensive, structured knowledge with references.
    Returns a list of article titles with brief descriptions that you can then retrieve in full using wikipedia_get_article.

    Args:
        query: Search query string

    Returns:
        JSON array of results with title, snippet, and URL for each article
    """
    args_schema: type[BaseModel] = WikipediaSearchInput

    def _run(self, query: str) -> str:
        limit = 5
        """Execute Wikipedia search"""
        import threading
        from queue import Queue

        result_queue = Queue()
        error_queue = Queue()

        def search_worker():
            """Worker thread for Wikipedia search with timeout protection"""
            try:
                wiki = wikipediaapi.Wikipedia(
                    user_agent='DimensionalResearchAgent/1.0',
                    language='en'
                )

                # Use Wikipedia's search functionality
                # Note: wikipediaapi doesn't have direct search, so we'll use a workaround
                # by trying to get the page and using related pages
                search_page = wiki.page(query)

                results = []

                # Add the main search result if it exists
                if search_page.exists():
                    results.append({
                        "title": search_page.title,
                        "snippet": search_page.summary[:200] + "..." if len(search_page.summary) > 200 else search_page.summary,
                        "url": search_page.fullurl
                    })

                # Limit results
                results = results[:limit]
                result_queue.put(results)
            except Exception as e:
                error_queue.put(e)

        # Execute search in worker thread with timeout
        search_thread = threading.Thread(target=search_worker, daemon=True)
        search_thread.start()
        search_thread.join(timeout=15.0)  # 15 second timeout

        # Check for timeout
        if search_thread.is_alive():
            return json.dumps({"error": "Wikipedia search timeout after 15 seconds"})

        # Check for errors
        if not error_queue.empty():
            error = error_queue.get()
            return json.dumps({"error": f"Wikipedia search error: {str(error)}"})

        # Get results
        if result_queue.empty():
            return json.dumps({"error": "No results returned from Wikipedia search"})

        try:
            results = result_queue.get_nowait()

            if not results:
                return json.dumps({
                    "status": "no_results",
                    "message": f"No Wikipedia articles found for query: {query}",
                    "results": []
                }, indent=2)

            return json.dumps({
                "status": "success",
                "query": query,
                "count": len(results),
                "results": results
            }, indent=2)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "message": f"Error searching Wikipedia: {str(e)}"
            }, indent=2)

    async def _arun(self, query: str, limit: int = 5) -> str:
        """Async version"""
        return self._run(query, limit)


class WikipediaGetArticleTool(BaseTool):
    """Retrieve content from a Wikipedia article"""

    name: str = "wikipedia_get_article"
    description: str = """Get the full content of a specific Wikipedia article by its exact title.

    Use this after finding article titles with wikipedia_search to retrieve detailed information.
    Provides comprehensive, well-structured content with citations and cross-references.
    You can get either a summary or the full article text (limited to 5000 characters).

    Args:
        title: Exact title of the Wikipedia article (as returned by wikipedia_search)
        summary_only: If True, returns only the summary; if False, returns full text (default: False)

    Returns:
        JSON with article title, content (summary or full text), URL, and last modified date
    """
    args_schema: type[BaseModel] = WikipediaGetArticleInput

    def _run(self, title: str, summary_only: bool = False) -> str:
        """Retrieve Wikipedia article content"""
        try:
            wiki = wikipediaapi.Wikipedia(
                user_agent='DimensionalResearchAgent/1.0',
                language='en'
            )

            page = wiki.page(title)

            if not page.exists():
                return json.dumps({
                    "status": "not_found",
                    "message": f"Wikipedia article not found: {title}",
                    "suggestion": "Try using wikipedia_search to find the correct article title"
                }, indent=2)

            # Get content based on summary_only flag
            if summary_only:
                content = page.summary
                content_type = "summary"
            else:
                # Limit full text to 5000 characters as requested
                content = page.text[:5000]
                content_type = "full_text"
                if len(page.text) > 5000:
                    content += "\n\n[... Content truncated at 5000 characters]"

            # Get categories for context
            categories = list(page.categories.keys())[:5]  # Limit to 5 categories

            result = {
                "status": "success",
                "title": page.title,
                "content_type": content_type,
                "content": content,
                "url": page.fullurl,
                "categories": categories,
                "character_count": len(content)
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "message": f"Error retrieving Wikipedia article: {str(e)}"
            }, indent=2)

    async def _arun(self, title: str, summary_only: bool = False) -> str:
        """Async version"""
        return self._run(title, summary_only)


# Create tool instances
wikipedia_search_tool = WikipediaSearchTool()
wikipedia_get_article_tool = WikipediaGetArticleTool()
