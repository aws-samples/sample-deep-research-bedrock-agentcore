"""
Tool loader for LangGraph integration
Loads tools from catalog and Gateway for use in research workflow
"""
import asyncio
from typing import List, Any, Optional
import logging

from src.adapters.multi_server_adapter import get_gateway_client
from src.catalog.tool_catalog import get_catalog
from src.catalog.tool_mappings import get_tools_by_research_type

# LangChain MCP adapter
try:
    from langchain_mcp_adapters.tools import load_mcp_tools
    MCP_TOOLS_AVAILABLE = True
except ImportError:
    MCP_TOOLS_AVAILABLE = False

logger = logging.getLogger(__name__)


async def load_tools_for_research_type(
    research_type: str,
    include_local: bool = True
) -> List[Any]:
    """
    Load all tools for a specific research type
    Combines Gateway tools and local tools

    Args:
        research_type: Research type (e.g., 'academic', 'financial')
        include_local: Whether to include local tools

    Returns:
        List of LangChain tool objects ready for use
    """
    logger.debug(f"📦 Loading tools for research type: {research_type}")

    tools = []

    # 1. Load Gateway tools
    try:
        gateway_tools = await load_gateway_tools_for_research_type(research_type)
        tools.extend(gateway_tools)
        logger.info(f"✅ Loaded {len(gateway_tools)} Gateway tools")
    except Exception as e:
        logger.error(f"Failed to load Gateway tools: {e}")
        logger.warning("Continuing without Gateway tools")

    # 2. Load local tools (if requested)
    if include_local:
        try:
            local_tools = load_local_tools()
            tools.extend(local_tools)
            logger.info(f"✅ Loaded {len(local_tools)} local tools")
        except Exception as e:
            logger.error(f"Failed to load local tools: {e}")

    logger.info(f"📊 Total tools loaded: {len(tools)}")
    return tools


def extract_tool_name(full_name: str) -> str:
    """
    Extract tool name from Gateway format.

    Gateway returns names like: target___tool_name
    We want just: tool_name

    Args:
        full_name: Full Gateway tool name

    Returns:
        Short tool name
    """
    if '___' in full_name:
        return full_name.split('___')[-1]
    return full_name


async def load_gateway_tools_for_research_type(research_type: str) -> List[Any]:
    """
    Load Gateway tools for a specific research type
    Uses MultiServerMCPClient and tool mappings

    Args:
        research_type: Research type

    Returns:
        List of LangChain tool objects compatible with Bedrock
    """
    if not MCP_TOOLS_AVAILABLE:
        logger.warning("langchain_mcp_adapters not available, Gateway tools disabled")
        return []

    # Get Gateway client and catalog
    client = await get_gateway_client()
    catalog = get_catalog()

    # Discover Gateway tools if not already in catalog
    if not catalog.list_by_source(catalog._tools.get(list(catalog._tools.keys())[0], None).__class__ if catalog._tools else None):
        async with client.session() as session:
            await catalog.discover_gateway_tools(session)

    # Get tool names for this research type
    required_tool_names = set(get_tools_by_research_type(research_type))

    logger.debug(f"Required tools for {research_type}: {required_tool_names}")

    # Load all tools from Gateway using MultiServerMCPClient
    # The session is kept alive by the client, so tools can be invoked later
    all_gateway_tools = await client.get_tools()

    # Filter to only include tools for this research type
    # Gateway tool names are in format: target___tool_name
    # We need to extract the short name for matching
    filtered_tools = [
        tool for tool in all_gateway_tools
        if extract_tool_name(tool.name) in required_tool_names
    ]

    # Convert tools to Bedrock-compatible format
    bedrock_compatible_tools = []
    for tool in filtered_tools:
        try:
            # Check if args_schema is dict (JSON Schema format - needs conversion)
            if hasattr(tool, 'args_schema') and isinstance(tool.args_schema, dict):
                # Check if it's JSON Schema format (has 'properties')
                if 'properties' in tool.args_schema:
                    from pydantic import BaseModel, Field, create_model
                    from typing import Optional

                    # Build field definitions from JSON Schema
                    field_definitions = {}
                    properties = tool.args_schema.get('properties', {})
                    required_fields = tool.args_schema.get('required', [])

                    for field_name, field_schema in properties.items():
                        # Determine Python type from JSON Schema type
                        field_type = str  # Default
                        schema_type = field_schema.get('type', 'string')

                        if schema_type == 'integer':
                            field_type = int
                        elif schema_type == 'number':
                            field_type = float
                        elif schema_type == 'boolean':
                            field_type = bool
                        elif schema_type == 'array':
                            field_type = list
                        elif schema_type == 'object':
                            field_type = dict

                        # Make field optional if not in required list
                        if field_name not in required_fields:
                            field_type = Optional[field_type]

                        field_desc = field_schema.get('description', '')

                        # Create field with default if optional
                        if field_name not in required_fields:
                            field_definitions[field_name] = (field_type, Field(default=None, description=field_desc))
                        else:
                            field_definitions[field_name] = (field_type, Field(description=field_desc))

                    # Create Pydantic model
                    ArgsModel = create_model(
                        f"{tool.name.replace('-', '_').replace('___', '_')}_args",
                        **field_definitions
                    )

                    # Recreate tool with Pydantic args_schema
                    from langchain_core.tools import StructuredTool
                    import asyncio

                    # Simplify tool name for Bedrock compatibility
                    # Remove target prefix and special characters
                    simple_name = extract_tool_name(tool.name).replace('-', '_')

                    # Get original coroutine (async only - use ainvoke)
                    original_coroutine = tool.coroutine if hasattr(tool, 'coroutine') else None

                    # Create tool with async support only
                    # Note: Must use agent.ainvoke() instead of agent.invoke()
                    new_tool = StructuredTool(
                        name=simple_name,
                        description=tool.description,
                        coroutine=original_coroutine,
                        args_schema=ArgsModel
                    )

                    bedrock_compatible_tools.append(new_tool)
                    logger.debug(f"Converted tool: {tool.name} -> {simple_name}")
                else:
                    # dict but not JSON Schema - keep as is
                    bedrock_compatible_tools.append(tool)
            else:
                # Already Pydantic model or not dict - keep as is
                bedrock_compatible_tools.append(tool)
        except Exception as e:
            logger.warning(f"Could not convert tool {tool.name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Keep original tool
            bedrock_compatible_tools.append(tool)

    logger.debug(
        f"Filtered {len(bedrock_compatible_tools)}/{len(all_gateway_tools)} "
        f"Gateway tools for {research_type} (Bedrock-compatible)"
    )

    return bedrock_compatible_tools


def load_local_tools() -> List[Any]:
    """
    Load local Python tools

    Includes code_interpreter tools for chart generation (optional for research agents).
    These tools use Bedrock Code Interpreter for safe Python execution.

    Returns:
        List of local LangChain tool objects
    """
    tools = []

    # Load code interpreter tools (3 tools: read, generate, insert)
    try:
        from src.tools.code_interpreter_tool import (
            read_document_lines,
            generate_and_validate_chart,
            bring_and_insert_chart
        )
        tools.extend([read_document_lines, generate_and_validate_chart, bring_and_insert_chart])
        logger.debug(f"Loaded {len(tools)} code_interpreter tools")
    except ImportError as e:
        logger.warning(f"Could not load code_interpreter tools: {e}")

    return tools


async def discover_and_catalog_tools() -> int:
    """
    Discover all available tools and add to catalog
    Should be called during initialization

    Returns:
        Number of tools discovered
    """
    logger.info("🔍 Discovering all available tools...")

    catalog = get_catalog()
    client = await get_gateway_client()

    # Discover Gateway tools
    async with client.session() as session:
        gateway_tools = await catalog.discover_gateway_tools(session)

    # Register local tools
    local_tools = load_local_tools()
    catalog.register_local_tools(local_tools)

    total = len(gateway_tools) + len(local_tools)
    logger.info(f"✅ Discovered {total} tools total")

    return total


async def validate_tools_for_research_type(research_type: str) -> dict:
    """
    Validate that all required tools for a research type are available

    Args:
        research_type: Research type to validate

    Returns:
        Dict with validation results
    """
    catalog = get_catalog()
    required_tools = set(get_tools_by_research_type(research_type))
    available_tools = set(catalog.list_names())

    missing = required_tools - available_tools
    extra = available_tools - required_tools

    return {
        "research_type": research_type,
        "required": len(required_tools),
        "available": len(available_tools & required_tools),
        "missing": list(missing),
        "valid": len(missing) == 0
    }


# ============================================================================
# Tool Initialization Helper
# ============================================================================

class ToolManager:
    """
    Manages tool loading and caching for research workflows
    """

    def __init__(self):
        self._tools_cache: dict[str, List[Any]] = {}
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self):
        """Initialize tool discovery and catalog (thread-safe)"""
        # Double-check locking pattern for async
        if self._initialized:
            return

        async with self._init_lock:
            # Check again after acquiring lock
            if self._initialized:
                return

            logger.info("🚀 Initializing Tool Manager...")
            await discover_and_catalog_tools()
            self._initialized = True
            logger.info("✅ Tool Manager initialized")

    async def get_tools(self, research_type: str, force_refresh: bool = False) -> List[Any]:
        """
        Get tools for research type with caching

        Args:
            research_type: Research type
            force_refresh: Bypass cache

        Returns:
            List of tools
        """
        if not self._initialized:
            await self.initialize()

        # Check cache
        if not force_refresh and research_type in self._tools_cache:
            logger.debug(f"Using cached tools for {research_type}")
            return self._tools_cache[research_type]

        # Load tools
        tools = await load_tools_for_research_type(research_type)

        # Cache
        self._tools_cache[research_type] = tools

        return tools

    async def validate(self, research_type: str) -> dict:
        """Validate tools for research type"""
        if not self._initialized:
            await self.initialize()

        return await validate_tools_for_research_type(research_type)

    def clear_cache(self):
        """Clear tool cache"""
        self._tools_cache.clear()
        logger.info("Tool cache cleared")


# Global tool manager
_tool_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    """Get global tool manager instance"""
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ToolManager()
    return _tool_manager
