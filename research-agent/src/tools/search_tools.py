"""Search tools for research workflow"""

import json
from typing import Dict, Any, List
from langchain_core.tools import tool

try:
    # Try new ddgs import (version >= 9.0.0)
    from ddgs import DDGS
    USE_NEW_DDGS = True
except ImportError:
    # Fallback to old DuckDuckGoSearchAPIWrapper
    from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
    USE_NEW_DDGS = False
    search_wrapper = DuckDuckGoSearchAPIWrapper()


@tool
def ddg_search(query: str) -> str:
    """
    Search the web using DuckDuckGo for general information, articles, and technical documentation.
    Good for finding recent developments, blog posts, technical guides, and broad web content.
    Returns titles, snippets, and links for each result (up to 5 results).

    Args:
        query: Search query string

    Returns:
        JSON string containing search results with title, snippet, and link
    """
    import threading
    from queue import Queue

    max_results = 5
    result_queue = Queue()
    error_queue = Queue()

    def search_worker():
        """Worker thread for search with timeout protection"""
        try:
            if USE_NEW_DDGS:
                # Use new DDGS API (version >= 9.0.0)
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
            else:
                # Use old wrapper API
                results = search_wrapper.results(query, max_results=max_results)
            result_queue.put(results)
        except Exception as e:
            error_queue.put(e)

    # Execute search in worker thread with timeout
    search_thread = threading.Thread(target=search_worker, daemon=True)
    search_thread.start()
    search_thread.join(timeout=15.0)  # 15 second timeout

    # Check for timeout
    if search_thread.is_alive():
        return json.dumps({"error": "Search timeout after 15 seconds"})

    # Check for errors
    if not error_queue.empty():
        error = error_queue.get()
        return json.dumps({"error": str(error)})

    # Get results
    if result_queue.empty():
        return json.dumps({"error": "No results returned from search"})

    try:
        results = result_queue.get_nowait()

        # Format results
        formatted_results = []
        for idx, result in enumerate(results):
            formatted_results.append({
                "index": idx + 1,
                "title": result.get("title", "No title"),
                "snippet": result.get("body", result.get("snippet", "No snippet")),
                "link": result.get("href", result.get("link", "No link"))
            })

        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def ddg_news(query: str, timelimit: str = None) -> str:
    """
    Search for recent news articles using DuckDuckGo News.
    Useful for finding latest developments, breaking news, and current events on a topic.
    Can filter by time period (day, week, or month). Returns up to 5 results.

    Args:
        query: Search query string
        timelimit: Time limit for news ('d' for day, 'w' for week, 'm' for month)

    Returns:
        JSON string containing news articles with publication date, title, body, and URL
    """
    max_results = 5
    try:
        if USE_NEW_DDGS:
            # Use new DDGS API (version >= 9.0.0)
            with DDGS() as ddgs:
                results = list(ddgs.news(
                    query=query,
                    max_results=max_results,
                    timelimit=timelimit
                ))
        else:
            # Old API doesn't support news search
            return json.dumps({
                "error": "News search requires ddgs>=9.0.0",
                "suggestion": "Upgrade: pip install --upgrade ddgs"
            })

        # Format results
        formatted_results = []
        for idx, result in enumerate(results):
            formatted_results.append({
                "index": idx + 1,
                "title": result.get("title", "No title"),
                "body": result.get("body", "No content"),
                "url": result.get("url", "No URL"),
                "date": result.get("date", "No date"),
                "source": result.get("source", "Unknown source")
            })

        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


def direct_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Direct search function (not a tool, for node internal use).
    Note: This is for internal use by nodes, not by agents, so max_results parameter is kept.

    Args:
        query: Search query string
        max_results: Maximum number of results

    Returns:
        List of search result dictionaries
    """
    import logging
    import threading
    from queue import Queue

    logger = logging.getLogger(__name__)

    logger.info(f"🔍 Starting search: '{query[:80]}...'")

    # Use threading-based timeout (works in any thread, unlike signal)
    result_queue = Queue()
    error_queue = Queue()

    def search_worker():
        """Worker function to perform search in separate thread"""
        try:
            if USE_NEW_DDGS:
                # Use new DDGS API (version >= 9.0.0)
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
            else:
                # Use old wrapper API
                results = search_wrapper.results(query, max_results=max_results)
            result_queue.put(results)
        except Exception as e:
            error_queue.put(e)

    # Start search in worker thread
    search_thread = threading.Thread(target=search_worker, daemon=True)
    search_thread.start()

    # Wait with timeout (15 seconds)
    search_thread.join(timeout=15.0)

    # Check results
    if search_thread.is_alive():
        # Timeout occurred
        logger.error(f"⏱️ Search timeout after 15s for query: '{query[:80]}...'")
        return []

    # Check for errors
    if not error_queue.empty():
        error = error_queue.get()
        logger.error(f"❌ Search error: {type(error).__name__}: {error}")
        return []

    # Get results
    if result_queue.empty():
        logger.warning(f"⚠️ No results from search for query: '{query[:80]}...'")
        return []

    try:
        results = result_queue.get_nowait()

        formatted_results = []
        for idx, result in enumerate(results):
            formatted_results.append({
                "index": idx + 1,
                "title": result.get("title", "No title"),
                "snippet": result.get("body", result.get("snippet", "No snippet")),
                "link": result.get("href", result.get("link", "No link"))
            })

        logger.info(f"✅ Search completed: {len(formatted_results)} results")
        return formatted_results

    except Exception as e:
        logger.error(f"❌ Error formatting results: {e}")
        return []
