"""Hybrid mode configuration for testing with mock tools and real LLM

This module provides a modified research agent that uses mock search tools
instead of real APIs, while keeping real LLM calls for prompt testing.
"""

from typing import List
from src.config.research_config import ResearchConfig, ResearchToolType
from src.tools.mock_search_tools import (
    mock_arxiv_search,
    mock_arxiv_get_paper,
    mock_ddg_search,
    mock_ddg_news,
    mock_tavily_search,
    mock_tavily_extract,
    mock_google_web_search,
    mock_wikipedia_search,
    mock_wikipedia_get_article,
    mock_finance_stock_quote,
    mock_finance_stock_history,
    mock_finance_news,
    mock_finance_comprehensive_analysis
)


def build_hybrid_research_tools(config: ResearchConfig) -> List:
    """
    Build list of research tools for hybrid mode.

    Uses mock tools instead of real APIs, but these tools will be called by real LLM.

    Args:
        config: ResearchConfig specifying which tools to enable

    Returns:
        List of mock tool instances
    """
    tools = []

    if config.has_tool(ResearchToolType.ARXIV_SEARCH):
        tools.append(mock_arxiv_search)

    if config.has_tool(ResearchToolType.ARXIV_GET_PAPER):
        tools.append(mock_arxiv_get_paper)

    if config.has_tool(ResearchToolType.DDG_SEARCH):
        tools.append(mock_ddg_search)

    if config.has_tool(ResearchToolType.DDG_NEWS):
        tools.append(mock_ddg_news)

    if config.has_tool(ResearchToolType.TAVILY_SEARCH):
        tools.append(mock_tavily_search)

    if config.has_tool(ResearchToolType.TAVILY_EXTRACT):
        tools.append(mock_tavily_extract)

    if config.has_tool(ResearchToolType.GOOGLE_WEB_SEARCH):
        tools.append(mock_google_web_search)

    if config.has_tool(ResearchToolType.GOOGLE_IMAGE_SEARCH):
        # Skip image search in hybrid mode
        pass

    if config.has_tool(ResearchToolType.WIKIPEDIA_SEARCH):
        tools.append(mock_wikipedia_search)

    if config.has_tool(ResearchToolType.WIKIPEDIA_GET_ARTICLE):
        tools.append(mock_wikipedia_get_article)

    if config.has_tool(ResearchToolType.FINANCE_STOCK_QUOTE):
        tools.append(mock_finance_stock_quote)

    if config.has_tool(ResearchToolType.FINANCE_STOCK_HISTORY):
        tools.append(mock_finance_stock_history)

    if config.has_tool(ResearchToolType.FINANCE_NEWS):
        tools.append(mock_finance_news)

    if config.has_tool(ResearchToolType.FINANCE_ANALYSIS):
        tools.append(mock_finance_comprehensive_analysis)

    return tools


def get_hybrid_search_results(query: str, max_results: int = 3) -> List:
    """
    Get mock search results for hybrid mode (used in non-agent nodes).

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        List of mock search result dicts
    """
    return [
        {
            "title": f"Overview of {query}",
            "snippet": f"Comprehensive introduction to {query} covering key concepts and applications.",
            "url": f"https://example.com/{hash(query) % 1000}"
        },
        {
            "title": f"{query}: Technical Guide",
            "snippet": f"Detailed technical guide for {query} with examples and best practices.",
            "url": f"https://docs.example.com/{hash(query) % 1000}"
        },
        {
            "title": f"Latest Developments in {query}",
            "snippet": f"Recent advances and trends in {query} based on industry research.",
            "url": f"https://research.example.com/{hash(query) % 1000}"
        }
    ][:max_results]
