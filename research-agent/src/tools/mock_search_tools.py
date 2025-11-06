"""Mock search tools for hybrid testing mode

These tools return compact, realistic mock data instead of calling real APIs.
Used with real LLM calls for fast testing of prompts and workflow logic.
"""

from langchain.tools import tool
from typing import List, Dict, Any
import json


@tool
def mock_arxiv_search(query: str) -> str:
    """Mock ArXiv search. Returns compact sample papers without API calls.

    Args:
        query: Search query for ArXiv papers

    Returns:
        JSON string with mock paper results
    """
    # Generate 3 mock papers
    mock_papers = [
        {
            "title": f"Advances in {query}: A Comprehensive Survey",
            "authors": ["John Smith", "Jane Doe"],
            "summary": f"This paper provides a comprehensive overview of recent developments in {query}. We analyze current approaches, identify key challenges, and propose future research directions. Our findings suggest significant potential for practical applications.",
            "arxiv_id": "2401.12345",
            "published": "2024-01-15",
            "url": "https://arxiv.org/abs/2401.12345"
        },
        {
            "title": f"Practical Applications of {query} in Enterprise Systems",
            "authors": ["Alice Johnson", "Bob Williams"],
            "summary": f"We present novel applications of {query} in enterprise environments. Through case studies and empirical analysis, we demonstrate improved performance and scalability. Results show 30% efficiency gains in real-world deployments.",
            "arxiv_id": "2402.67890",
            "published": "2024-02-20",
            "url": "https://arxiv.org/abs/2402.67890"
        },
        {
            "title": f"Theoretical Foundations of {query}",
            "authors": ["Carol Martinez", "David Lee"],
            "summary": f"This work establishes theoretical foundations for {query}. We prove convergence properties, analyze complexity bounds, and provide formal guarantees. The framework unifies previous approaches under a common mathematical foundation.",
            "arxiv_id": "2403.11111",
            "published": "2024-03-10",
            "url": "https://arxiv.org/abs/2403.11111"
        }
    ]

    return json.dumps({
        "status": "success",
        "query": query,
        "results": mock_papers,
        "count": len(mock_papers)
    }, indent=2)


@tool
def mock_arxiv_get_paper(arxiv_id: str) -> str:
    """Mock ArXiv paper retrieval. Returns compact paper content without API calls.

    Args:
        arxiv_id: ArXiv paper ID

    Returns:
        JSON string with mock paper details
    """
    return json.dumps({
        "status": "success",
        "arxiv_id": arxiv_id,
        "title": f"Detailed Analysis of Paper {arxiv_id}",
        "authors": ["Research Team"],
        "abstract": f"This paper (ID: {arxiv_id}) presents comprehensive research with detailed methodology, experimental results, and theoretical analysis. Key contributions include novel algorithms, empirical validation, and practical guidelines for implementation.",
        "sections": {
            "introduction": "Background and motivation for this research area.",
            "methodology": "Detailed description of our approach and experimental setup.",
            "results": "Experimental findings show significant improvements over baselines.",
            "conclusions": "Summary of contributions and future research directions."
        }
    }, indent=2)


@tool
def mock_ddg_search(query: str) -> str:
    """Mock DuckDuckGo web search. Returns compact web results without API calls.

    Args:
        query: Search query

    Returns:
        JSON string with mock web results
    """
    mock_results = [
        {
            "title": f"Complete Guide to {query}",
            "url": f"https://example.com/guide-{hash(query) % 1000}",
            "snippet": f"Comprehensive guide covering all aspects of {query}. Learn fundamentals, best practices, and advanced techniques. Updated for 2024 with latest developments and industry trends."
        },
        {
            "title": f"{query}: Latest Trends and Analysis",
            "url": f"https://techblog.com/analysis-{hash(query) % 1000}",
            "snippet": f"In-depth analysis of current trends in {query}. Expert insights, case studies, and practical examples. Discover how leading companies are implementing these technologies."
        },
        {
            "title": f"Getting Started with {query}",
            "url": f"https://docs.example.org/intro-{hash(query) % 1000}",
            "snippet": f"Beginner-friendly introduction to {query}. Step-by-step tutorials, code examples, and troubleshooting tips. Perfect for developers and technical teams."
        }
    ]

    return json.dumps({
        "status": "success",
        "query": query,
        "results": mock_results,
        "count": len(mock_results)
    }, indent=2)


@tool
def mock_ddg_news(query: str) -> str:
    """Mock DuckDuckGo news search. Returns compact news results without API calls.

    Args:
        query: Search query

    Returns:
        JSON string with mock news results
    """
    mock_news = [
        {
            "title": f"Breaking: Major Breakthrough in {query}",
            "url": f"https://technews.com/story-{hash(query) % 1000}",
            "snippet": f"Researchers announce significant advancement in {query}. New approach shows promising results with potential real-world impact. Industry experts call it a game-changer.",
            "date": "2024-06-15",
            "source": "Tech News Daily"
        },
        {
            "title": f"{query} Adoption Grows Among Enterprises",
            "url": f"https://biztech.com/report-{hash(query) % 1000}",
            "snippet": f"Survey shows 60% of enterprises now using {query} in production. Benefits include improved efficiency, cost savings, and competitive advantages. Market expected to grow 40% annually.",
            "date": "2024-06-10",
            "source": "Business Technology"
        }
    ]

    return json.dumps({
        "status": "success",
        "query": query,
        "results": mock_news,
        "count": len(mock_news)
    }, indent=2)


@tool
def mock_tavily_search(query: str) -> str:
    """Mock Tavily search. Returns compact results without API calls.

    Args:
        query: Search query

    Returns:
        JSON string with mock results
    """
    mock_results = [
        {
            "title": f"Comprehensive Overview: {query}",
            "url": f"https://research.example.com/{hash(query) % 1000}",
            "content": f"Detailed analysis of {query} covering technical architecture, implementation patterns, and use cases. Includes benchmarks, comparisons, and best practices from industry leaders.",
            "score": 0.95
        },
        {
            "title": f"Technical Deep Dive: {query}",
            "url": f"https://engineering.blog.com/{hash(query) % 1000}",
            "content": f"Engineering perspective on {query} with code examples and architectural diagrams. Covers performance optimization, scalability considerations, and production deployment strategies.",
            "score": 0.89
        }
    ]

    return json.dumps({
        "status": "success",
        "query": query,
        "results": mock_results
    }, indent=2)


@tool
def mock_tavily_extract(urls: List[str]) -> str:
    """Mock Tavily content extraction. Returns compact content without API calls.

    Args:
        urls: List of URLs to extract content from

    Returns:
        JSON string with mock extracted content
    """
    extracted = []
    for url in urls:
        extracted.append({
            "url": url,
            "title": f"Article from {url.split('/')[2] if '/' in url else 'source'}",
            "content": f"""
# Introduction
This article provides comprehensive coverage of the topic from {url}.

## Key Points
- Detailed technical analysis with specific examples
- Performance benchmarks and scalability considerations
- Best practices and implementation guidelines
- Real-world case studies from production deployments

## Methodology
The approach combines theoretical foundations with practical applications.

## Results
Experimental validation shows significant improvements over existing methods.

## Conclusions
These findings enable more efficient and effective implementations.
""",
            "metadata": {
                "length": 500,
                "extracted_at": "2024-06-15"
            }
        })

    return json.dumps({
        "status": "success",
        "results": extracted,
        "count": len(extracted)
    }, indent=2)


@tool
def mock_google_web_search(query: str) -> str:
    """Mock Google web search. Returns compact results without API calls.

    Args:
        query: Search query

    Returns:
        JSON string with mock results
    """
    mock_results = [
        {
            "title": f"Official Documentation - {query}",
            "link": f"https://docs.example.com/{hash(query) % 1000}",
            "snippet": f"Official documentation for {query}. Complete API reference, tutorials, and integration guides. Maintained by the core development team."
        },
        {
            "title": f"Industry Report: {query} Market Analysis",
            "link": f"https://reports.example.com/{hash(query) % 1000}",
            "snippet": f"Market analysis and trends for {query}. Growth forecasts, competitive landscape, and strategic recommendations. Based on surveys of 500+ organizations."
        },
        {
            "title": f"{query} - Wikipedia",
            "link": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            "snippet": f"Wikipedia article covering history, technical details, and applications of {query}. Comprehensive overview with citations to academic sources."
        }
    ]

    return json.dumps({
        "status": "success",
        "query": query,
        "results": mock_results
    }, indent=2)


@tool
def mock_wikipedia_search(query: str, limit: int = 3) -> str:
    """Mock Wikipedia search. Returns compact results without API calls.

    Args:
        query: Search query
        limit: Maximum results to return

    Returns:
        JSON string with mock Wikipedia results
    """
    mock_results = [
        {
            "title": query.title(),
            "pageid": hash(query) % 100000,
            "snippet": f"{query} refers to a field of study and technology involving... Multiple applications exist in industry and research. The field has evolved significantly since its inception."
        },
        {
            "title": f"History of {query}",
            "pageid": hash(query + "history") % 100000,
            "snippet": f"The history of {query} traces back to early research in the 1990s. Major developments include theoretical breakthroughs, practical implementations, and widespread adoption."
        },
        {
            "title": f"Applications of {query}",
            "pageid": hash(query + "applications") % 100000,
            "snippet": f"Applications of {query} span multiple domains including enterprise systems, research environments, and consumer products. Used by millions worldwide."
        }
    ][:limit]

    return json.dumps({
        "status": "success",
        "query": query,
        "results": mock_results
    }, indent=2)


@tool
def mock_wikipedia_get_article(title: str) -> str:
    """Mock Wikipedia article retrieval. Returns compact article without API calls.

    Args:
        title: Article title

    Returns:
        JSON string with mock article content
    """
    return json.dumps({
        "status": "success",
        "title": title,
        "content": f"""
# {title}

{title} is a significant concept in modern technology and research.

## Overview
This field encompasses various techniques, methodologies, and applications that have transformed the industry.

## History
Development began in the early 2000s with foundational research. Key milestones include:
- Initial theoretical frameworks (2005)
- First practical implementations (2010)
- Widespread commercial adoption (2015)
- Current advanced applications (2020-present)

## Technical Details
The technical architecture involves multiple components working together:
- Core processing layer
- Data management systems
- Interface and integration layers
- Monitoring and optimization tools

## Applications
Common applications include:
- Enterprise data processing
- Real-time analytics
- Machine learning workflows
- System integration and automation

## Future Directions
Ongoing research focuses on scalability, efficiency, and novel applications.

## References
Multiple academic papers and industry reports document these developments.
""",
        "summary": f"Comprehensive article about {title} covering technical aspects, applications, and future directions."
    }, indent=2)


# Mock finance tools
@tool
def mock_finance_stock_quote(symbol: str) -> str:
    """Mock stock quote. Returns sample data without API calls."""
    return json.dumps({
        "symbol": symbol.upper(),
        "price": 150.25,
        "change": 2.34,
        "change_percent": 1.58,
        "volume": 12500000,
        "market_cap": "2.5T"
    }, indent=2)


@tool
def mock_finance_stock_history(symbol: str, period: str = "1mo") -> str:
    """Mock stock history. Returns sample data without API calls."""
    return json.dumps({
        "symbol": symbol.upper(),
        "period": period,
        "data_points": 20,
        "trend": "upward",
        "summary": f"Over {period}, {symbol} showed positive momentum with 5% gains."
    }, indent=2)


@tool
def mock_finance_news(symbol: str) -> str:
    """Mock financial news. Returns sample data without API calls."""
    return json.dumps({
        "symbol": symbol.upper(),
        "articles": [
            {
                "title": f"{symbol} Reports Strong Quarterly Results",
                "summary": "Company exceeds analyst expectations with revenue growth.",
                "date": "2024-06-15"
            },
            {
                "title": f"Analysts Upgrade {symbol} Price Target",
                "summary": "Multiple firms raise price targets citing strong fundamentals.",
                "date": "2024-06-10"
            }
        ]
    }, indent=2)


@tool
def mock_finance_comprehensive_analysis(symbol: str) -> str:
    """Mock comprehensive financial analysis. Returns sample data without API calls."""
    return json.dumps({
        "symbol": symbol.upper(),
        "fundamentals": {
            "pe_ratio": 25.3,
            "revenue_growth": "12%",
            "profit_margin": "28%"
        },
        "technical": {
            "trend": "bullish",
            "support": 145.0,
            "resistance": 155.0
        },
        "analysis": f"Comprehensive analysis of {symbol} shows strong fundamentals and positive technical indicators."
    }, indent=2)
