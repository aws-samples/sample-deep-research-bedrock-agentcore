"""
DuckDuckGo Search Lambda for AgentCore Gateway
Provides web search and news search
"""
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import after logger setup
from ddgs import DDGS

def lambda_handler(event, context):
    """
    Lambda handler for DuckDuckGo tools via AgentCore Gateway

    Gateway unwraps tool arguments and passes them directly to Lambda
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Get tool name from context (set by AgentCore Gateway)
        tool_name = 'unknown'
        if hasattr(context, 'client_context') and context.client_context:
            if hasattr(context.client_context, 'custom'):
                tool_name = context.client_context.custom.get('bedrockAgentCoreToolName', '')
                if '___' in tool_name:
                    tool_name = tool_name.split('___')[-1]

        logger.info(f"Tool name: {tool_name}")

        # Route to appropriate tool
        if tool_name == 'ddg_search':
            return ddg_search(event)
        elif tool_name == 'ddg_news':
            return ddg_news(event)
        else:
            return error_response(f"Unknown tool: {tool_name}")

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e))


def ddg_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute DuckDuckGo web search"""

    # Extract parameters (Gateway unwraps them)
    query = params.get('query')
    max_results = 5

    if not query:
        return error_response("query parameter required")

    logger.info(f"DuckDuckGo search: query={query}")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        # Format results
        formatted_results = []
        for idx, result in enumerate(results, 1):
            formatted_results.append({
                "index": idx,
                "title": result.get("title", "No title"),
                "snippet": result.get("body", result.get("snippet", "No snippet")),
                "link": result.get("href", result.get("link", "No link"))
            })

        result_data = {
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results
        }

        return success_response(json.dumps(result_data, indent=2))

    except Exception as e:
        return error_response(f"DuckDuckGo search error: {str(e)}")


def ddg_news(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute DuckDuckGo news search"""

    # Extract parameters
    query = params.get('query')
    timelimit = params.get('timelimit')  # 'd', 'w', or 'm'
    max_results = 5

    if not query:
        return error_response("query parameter required")

    logger.info(f"DuckDuckGo news: query={query}, timelimit={timelimit}")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(
                query=query,
                max_results=max_results,
                timelimit=timelimit
            ))

        # Format results
        formatted_results = []
        for idx, result in enumerate(results, 1):
            formatted_results.append({
                "index": idx,
                "title": result.get("title", "No title"),
                "body": result.get("body", "No content"),
                "url": result.get("url", "No URL"),
                "date": result.get("date", "No date"),
                "source": result.get("source", "Unknown source")
            })

        result_data = {
            "query": query,
            "timelimit": timelimit,
            "results_count": len(formatted_results),
            "results": formatted_results
        }

        return success_response(json.dumps(result_data, indent=2))

    except Exception as e:
        return error_response(f"DuckDuckGo news search error: {str(e)}")


def success_response(content: str) -> Dict[str, Any]:
    """Format successful MCP response"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'content': [{
                'type': 'text',
                'text': content
            }]
        })
    }


def error_response(message: str) -> Dict[str, Any]:
    """Format error response"""
    logger.error(f"Error response: {message}")
    return {
        'statusCode': 400,
        'body': json.dumps({
            'error': message
        })
    }
