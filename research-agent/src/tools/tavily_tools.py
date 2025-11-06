"""Tavily AI search tools for research"""

import os
import json
import requests
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool


class TavilySearchInput(BaseModel):
    """Input schema for Tavily search"""
    query: str = Field(..., description="Search query")
    search_depth: str = Field(default="basic", description="Search depth: 'basic' or 'advanced'")
    topic: str = Field(default="general", description="Search topic: 'general' or 'news'")


class TavilyExtractInput(BaseModel):
    """Input schema for Tavily content extraction"""
    urls: str = Field(..., description="Comma-separated URLs to extract content from")
    extract_depth: str = Field(default="basic", description="Extraction depth: 'basic' or 'advanced'")


class TavilySearchTool(BaseTool):
    """Tool for web search using Tavily AI"""

    name: str = "tavily_search"
    description: str = """Search the web using Tavily AI-powered search engine. Returns up to 5 results.

    Tavily uses AI to analyze search results and return the most relevant, high-quality content with detailed snippets.
    Superior to basic search for complex queries requiring semantic understanding and content relevance ranking.
    Supports both general web search and news-specific search with adjustable search depth (basic or advanced).
    Use this for research tasks requiring comprehensive, well-filtered results."""
    args_schema: Type[BaseModel] = TavilySearchInput

    def _run(
        self,
        query: str,
        search_depth: str = "basic",
        topic: str = "general"
    ) -> str:
        max_results = 5
        """Execute Tavily web search"""

        # Get API key
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return json.dumps({
                "error": "TAVILY_API_KEY not found in environment variables",
                "instructions": "Set TAVILY_API_KEY environment variable or in .env file"
            })

        # Validate inputs
        if not query or len(query.strip()) == 0:
            return json.dumps({"error": "Query cannot be empty"})

        max_results = max(1, min(max_results, 20))  # Clamp between 1-20

        # Prepare API request
        search_params = {
            "api_key": api_key,
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_images": False,
            "include_raw_content": False
        }

        try:
            # Make API request
            response = requests.post(
                "https://api.tavily.com/search",
                json=search_params,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            # Handle response codes
            if response.status_code == 401:
                return json.dumps({"error": "Invalid Tavily API key"})
            elif response.status_code == 429:
                return json.dumps({"error": "Tavily API rate limit exceeded"})
            elif response.status_code != 200:
                return json.dumps({
                    "error": f"Tavily API error: {response.status_code}",
                    "details": response.text
                })

            search_results = response.json()

            # Format results
            if not search_results.get('results'):
                return json.dumps({
                    "query": query,
                    "results": [],
                    "message": "No results found"
                })

            formatted_results = []
            for idx, result in enumerate(search_results.get('results', []), 1):
                formatted_results.append({
                    "index": idx,
                    "title": result.get('title', 'No title'),
                    "url": result.get('url', 'No URL'),
                    "content": result.get('content', 'No content'),
                    "score": result.get('score', 0),
                    "published_date": result.get('published_date', '')
                })

            result_data = {
                "query": query,
                "search_depth": search_depth,
                "topic": topic,
                "results_count": len(formatted_results),
                "results": formatted_results
            }

            return json.dumps(result_data, indent=2)

        except requests.exceptions.Timeout:
            return json.dumps({"error": "Tavily API request timed out"})
        except requests.exceptions.RequestException as e:
            return json.dumps({"error": f"Failed to connect to Tavily API: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Tavily search error: {str(e)}"})


class TavilyExtractTool(BaseTool):
    """Tool for extracting content from URLs using Tavily"""

    name: str = "tavily_extract"
    description: str = """Extract clean, readable content from specific web URLs using Tavily's AI-powered extraction.

    Intelligently removes ads, navigation bars, popups, and other boilerplate, returning only the main content.
    Excellent for retrieving full article text, blog posts, or documentation from URLs found in search results.
    Supports multiple URLs at once (comma-separated) and adjustable extraction depth (basic or advanced).
    Use this when you need the full content from a web page, not just a snippet."""
    args_schema: Type[BaseModel] = TavilyExtractInput

    def _run(
        self,
        urls: str,
        extract_depth: str = "basic"
    ) -> str:
        """Execute Tavily content extraction"""

        # Get API key
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return json.dumps({
                "error": "TAVILY_API_KEY not found in environment variables",
                "instructions": "Set TAVILY_API_KEY environment variable or in .env file"
            })

        # Parse URLs
        if not urls or len(urls.strip()) == 0:
            return json.dumps({"error": "URLs cannot be empty"})

        url_list = [url.strip() for url in urls.split(',') if url.strip()]
        if not url_list:
            return json.dumps({"error": "No valid URLs provided"})

        # Prepare API request
        extract_params = {
            "api_key": api_key,
            "urls": url_list,
            "extract_depth": extract_depth
        }

        try:
            # Make API request
            response = requests.post(
                "https://api.tavily.com/extract",
                json=extract_params,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            # Handle response codes
            if response.status_code == 401:
                return json.dumps({"error": "Invalid Tavily API key"})
            elif response.status_code == 429:
                return json.dumps({"error": "Tavily API rate limit exceeded"})
            elif response.status_code != 200:
                return json.dumps({
                    "error": f"Tavily API error: {response.status_code}",
                    "details": response.text
                })

            extract_results = response.json()

            # Format results
            if not extract_results.get('results'):
                return json.dumps({
                    "urls": url_list,
                    "results": [],
                    "message": "No content extracted"
                })

            formatted_results = []
            for idx, result in enumerate(extract_results.get('results', []), 1):
                url = result.get('url', 'No URL')
                content = result.get('raw_content', result.get('content', 'No content'))

                # Truncate very long content
                if len(content) > 5000:
                    content = content[:5000] + "... [Content truncated for length]"

                formatted_results.append({
                    "index": idx,
                    "url": url,
                    "content": content,
                    "content_length": len(result.get('raw_content', result.get('content', '')))
                })

            result_data = {
                "extract_depth": extract_depth,
                "urls_count": len(url_list),
                "results_count": len(formatted_results),
                "results": formatted_results
            }

            return json.dumps(result_data, indent=2)

        except requests.exceptions.Timeout:
            return json.dumps({"error": "Tavily API request timed out"})
        except requests.exceptions.RequestException as e:
            return json.dumps({"error": f"Failed to connect to Tavily API: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Tavily extraction error: {str(e)}"})


# Create tool instances
tavily_search_tool = TavilySearchTool()
tavily_extract_tool = TavilyExtractTool()

# Tool list
TAVILY_TOOLS = [tavily_search_tool, tavily_extract_tool]
