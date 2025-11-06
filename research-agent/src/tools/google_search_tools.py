"""Google Custom Search tools for web and image search"""

import os
import json
import requests
from typing import Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool


class GoogleWebSearchInput(BaseModel):
    """Input schema for Google web search"""
    query: str = Field(..., description="Search query")


class GoogleImageSearchInput(BaseModel):
    """Input schema for Google image search"""
    query: str = Field(..., description="Search query for images")


def check_image_accessible(url: str, timeout: int = 5) -> bool:
    """Check if image URL is accessible without downloading the full image"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://www.google.com/'
        }

        # Use HEAD request to check accessibility
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            return 'image' in content_type

        # If HEAD fails, try small range request
        if response.status_code == 405:
            headers['Range'] = 'bytes=0-1023'
            response = requests.get(url, headers=headers, timeout=timeout)
            return response.status_code in [200, 206]

        return False
    except Exception:
        return False


class GoogleWebSearchTool(BaseTool):
    """Tool for web search using Google Custom Search API"""

    name: str = "google_web_search"
    description: str = """Search the web using Google Custom Search API. Returns up to 5 results.

    Leverages Google's powerful search infrastructure and ranking algorithms to find authoritative, high-quality web content.
    Returns results with titles, links, and descriptive snippets. Excellent for finding established sources, technical documentation,
    official pages, and widely-referenced content. Use this when you need Google's comprehensive web index and relevance ranking."""
    args_schema: Type[BaseModel] = GoogleWebSearchInput

    def _run(self, query: str) -> str:
        num_results = 5
        """Execute Google web search"""

        # Get API credentials
        api_key = os.getenv("GOOGLE_API_KEY")
        search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        if not api_key or not search_engine_id:
            return json.dumps({
                "error": "Google API credentials not found",
                "instructions": "Set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env file"
            })

        # Validate inputs
        if not query or len(query.strip()) == 0:
            return json.dumps({"error": "Query cannot be empty"})

        num_results = max(1, min(num_results, 10))

        # Prepare API request
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': num_results,
            'safe': 'active'
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 400:
                return json.dumps({"error": "Invalid Google API request"})
            elif response.status_code == 403:
                return json.dumps({"error": "Google API key invalid or quota exceeded"})
            elif response.status_code != 200:
                return json.dumps({
                    "error": f"Google API error: {response.status_code}",
                    "details": response.text
                })

            data = response.json()

            # Format results
            results = []
            if 'items' in data:
                for idx, item in enumerate(data['items'], 1):
                    results.append({
                        "index": idx,
                        "title": item.get('title', 'No title'),
                        "link": item.get('link', 'No link'),
                        "snippet": item.get('snippet', 'No snippet')
                    })

            result_data = {
                "query": query,
                "results_count": len(results),
                "results": results
            }

            return json.dumps(result_data, indent=2)

        except requests.exceptions.Timeout:
            return json.dumps({"error": "Google API request timed out"})
        except requests.exceptions.RequestException as e:
            return json.dumps({"error": f"Failed to connect to Google API: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Google web search error: {str(e)}"})


class GoogleImageSearchTool(BaseTool):
    """Tool for image search using Google Custom Search API"""

    name: str = "google_image_search"
    description: str = """Search for images using Google's image search index. Returns up to 5 verified images.

    Returns accessible, verified image URLs with context metadata (title, source page, dimensions).
    Excellent for finding technical diagrams, architecture illustrations, charts, infographics, and visual examples.
    Automatically validates image accessibility before returning results. Use this when visual content would enhance research understanding."""
    args_schema: Type[BaseModel] = GoogleImageSearchInput

    def _run(self, query: str) -> str:
        num_results = 5
        """Execute Google image search"""

        # Get API credentials
        api_key = os.getenv("GOOGLE_API_KEY")
        search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        if not api_key or not search_engine_id:
            return json.dumps({
                "error": "Google API credentials not found",
                "instructions": "Set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env file"
            })

        # Validate inputs
        if not query or len(query.strip()) == 0:
            return json.dumps({"error": "Query cannot be empty"})

        num_results = max(1, min(num_results, 10))

        # Prepare API request
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'searchType': 'image',
            'num': 10,  # Get max results to filter for accessible ones
            'safe': 'active'
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 400:
                return json.dumps({"error": "Invalid Google API request"})
            elif response.status_code == 403:
                return json.dumps({"error": "Google API key invalid or quota exceeded"})
            elif response.status_code != 200:
                return json.dumps({
                    "error": f"Google API error: {response.status_code}",
                    "details": response.text
                })

            data = response.json()

            # Filter for accessible images
            accessible_results = []
            all_items = data.get('items', [])

            for item in all_items:
                image_url = item.get('link', '')

                if image_url and check_image_accessible(image_url):
                    accessible_results.append({
                        "title": item.get('title', 'Untitled'),
                        "link": item.get('link', 'No link'),
                        "snippet": item.get('snippet', 'No description'),
                        "image_url": image_url
                    })

                    # Stop when we have enough
                    if len(accessible_results) >= num_results:
                        break

            # Format results
            formatted_results = []
            for idx, r in enumerate(accessible_results, 1):
                formatted_results.append({
                    "index": idx,
                    "title": r['title'],
                    "link": r['link'],
                    "snippet": r['snippet'],
                    "image_url": r['image_url']
                })

            result_data = {
                "query": query,
                "results_count": len(formatted_results),
                "results": formatted_results
            }

            return json.dumps(result_data, indent=2)

        except requests.exceptions.Timeout:
            return json.dumps({"error": "Google API request timed out"})
        except requests.exceptions.RequestException as e:
            return json.dumps({"error": f"Failed to connect to Google API: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Google image search error: {str(e)}"})


# Create tool instances
google_web_search_tool = GoogleWebSearchTool()
google_image_search_tool = GoogleImageSearchTool()

# Tool list
GOOGLE_TOOLS = [google_web_search_tool, google_image_search_tool]
