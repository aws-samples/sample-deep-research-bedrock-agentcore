"""
Tool discovery from various sources
Automatically extracts metadata and maps to research types
"""
from typing import List, Any, Dict
from src.catalog.tool_catalog import ToolMetadata, ToolSource
from src.catalog.tool_mappings import (
    GATEWAY_TOOL_CATEGORIES,
    get_research_types_for_tool
)
import logging

logger = logging.getLogger(__name__)


async def discover_from_gateway(session) -> List[ToolMetadata]:
    """
    Discover tools from AgentCore Gateway
    Automatically categorizes and maps to research types

    Args:
        session: MCP ClientSession instance

    Returns:
        List of ToolMetadata for discovered tools
    """
    result = await session.list_tools()
    gateway_tools = result.tools

    discovered = []
    for tool in gateway_tools:
        name = tool.name

        # Get category from mappings
        category = GATEWAY_TOOL_CATEGORIES.get(name, "other")

        # Get research types that use this tool
        research_types = list(get_research_types_for_tool(name))

        # Extract parameters if available
        parameters = {}
        if hasattr(tool, 'inputSchema'):
            schema = tool.inputSchema
            if isinstance(schema, dict):
                parameters = schema.get("properties", {})

        meta = ToolMetadata(
            name=name,
            description=tool.description or f"Gateway tool: {name}",
            source=ToolSource.GATEWAY,
            category=category,
            parameters=parameters,
            gateway_name=name,
            research_types=research_types,
        )
        discovered.append(meta)

        logger.debug(
            f"Discovered Gateway tool: {name} "
            f"[{category}] for research types: {', '.join(research_types)}"
        )

    return discovered


def discover_from_local(tools: List[Any]) -> List[ToolMetadata]:
    """
    Discover local tools
    Extracts metadata from tool objects

    Args:
        tools: List of tool objects (LangChain tools or callable)

    Returns:
        List of ToolMetadata
    """
    discovered = []

    for tool in tools:
        try:
            # LangChain tool introspection
            if hasattr(tool, 'name'):
                name = tool.name
            elif hasattr(tool, '__name__'):
                name = tool.__name__
            else:
                name = str(tool)

            if hasattr(tool, 'description'):
                description = tool.description
            elif hasattr(tool, '__doc__'):
                description = tool.__doc__ or f'Local tool: {name}'
            else:
                description = f'Local tool: {name}'

            # Local tools typically work with all research types
            meta = ToolMetadata(
                name=name,
                description=description.strip(),
                source=ToolSource.LOCAL,
                category="local",
                research_types=[],  # Local tools available for all types
            )
            discovered.append(meta)

            logger.debug(f"Discovered local tool: {name}")

        except Exception as e:
            logger.warning(f"Could not extract metadata from tool {tool}: {e}")

    return discovered


def validate_tool_coverage(catalog) -> Dict[str, Any]:
    """
    Validate that all tools defined in mappings are available in catalog

    Args:
        catalog: ToolCatalog instance

    Returns:
        Dict with validation results
    """
    from src.catalog.tool_mappings import RESEARCH_TYPE_TOOLS

    missing_tools = {}
    available_tools = set(catalog.list_names())

    for research_type, expected_tools in RESEARCH_TYPE_TOOLS.items():
        missing = [t for t in expected_tools if t not in available_tools]
        if missing:
            missing_tools[research_type] = missing

    return {
        "valid": len(missing_tools) == 0,
        "missing_tools": missing_tools,
        "available_count": len(available_tools),
    }
