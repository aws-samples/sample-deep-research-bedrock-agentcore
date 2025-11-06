"""
MCP Adapter for AgentCore Gateway
Manages connection lifecycle, authentication, and tool routing
"""
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import logging

# MCP and auth imports
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    from src.utils.gateway_auth import get_sigv4_auth, get_gateway_region_from_url
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    _import_error = e

logger = logging.getLogger(__name__)


class MCPAdapter:
    """
    Manages MCP connections to AgentCore Gateway
    - AWS SigV4 authentication
    - Session lifecycle management
    - Tool discovery and caching

    Note: Each operation creates a new connection using context managers.
    This follows the MCP best practice pattern.
    """

    def __init__(self, gateway_url: str, region: Optional[str] = None):
        """
        Initialize MCP Adapter

        Args:
            gateway_url: AgentCore Gateway URL
            region: AWS region for SigV4 signing (auto-detected if not provided)
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                f"MCP dependencies not available: {_import_error}\n"
                "Please install: pip install mcp httpx anyio"
            )

        self.gateway_url = gateway_url

        # Auto-detect region from URL if not provided
        if region is None:
            region = get_gateway_region_from_url(gateway_url)
        self.region = region

        self._tools_cache: Optional[List[Any]] = None
        self._persistent_session: Optional[Any] = None  # Keep session alive
        self._session_context_stack = []  # Track context managers

        logger.debug(f"MCPAdapter initialized for {gateway_url} (region: {region})")

    async def _create_gateway_transport(self):
        """
        Create Gateway transport with SigV4 authentication.

        This follows the exact pattern from create_gateway_session in reference script.

        Returns:
            Context manager for streamable HTTP client
        """
        auth = get_sigv4_auth(region=self.region)
        return streamablehttp_client(url=self.gateway_url, auth=auth)

    @asynccontextmanager
    async def _create_session(self):
        """
        Create an authenticated MCP session.

        This follows the exact pattern from the working reference script:
        - Get transport (returns context manager)
        - Await the context manager
        - Use nested context managers for ClientSession

        Yields:
            ClientSession: Initialized MCP session
        """
        logger.debug(f"🔌 Creating Gateway session: {self.gateway_url}")

        # Use the exact pattern from reference script
        async with await self._create_gateway_transport() as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.debug("✅ MCP session initialized")
                yield session

    async def list_tools(self, force_refresh: bool = False) -> List[Any]:
        """
        List available tools from Gateway
        Uses cache for performance unless force_refresh=True

        Args:
            force_refresh: If True, bypass cache and fetch fresh list

        Returns:
            List of tool objects from Gateway
        """
        if self._tools_cache and not force_refresh:
            logger.debug(f"Using cached tools list ({len(self._tools_cache)} tools)")
            return self._tools_cache

        try:
            async with self._create_session() as session:
                result = await session.list_tools()
                self._tools_cache = result.tools
                logger.debug(f"📦 Discovered {len(self._tools_cache)} tools from Gateway")
                return self._tools_cache
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a Gateway tool

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as dictionary

        Returns:
            Tool result

        Raises:
            Exception: If tool call fails
        """
        try:
            logger.debug(f"🔧 Calling tool: {tool_name}")
            async with self._create_session() as session:
                result = await session.call_tool(tool_name, arguments)
                logger.debug(f"✅ Tool call successful: {tool_name}")
                return result
        except Exception as e:
            logger.error(f"❌ Tool call failed: {tool_name}, error: {e}")
            raise

    @asynccontextmanager
    async def get_session(self):
        """
        Context manager for session access

        Usage:
            async with adapter.get_session() as session:
                tools = await session.list_tools()
        """
        async with self._create_session() as session:
            yield session

    async def health_check(self) -> bool:
        """
        Check if Gateway is accessible and responsive

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.list_tools()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


# ============================================================================
# Global Adapter Management
# ============================================================================

_adapter: Optional[MCPAdapter] = None
_adapter_lock = asyncio.Lock()


async def get_adapter(gateway_url: str = None, region: str = None) -> MCPAdapter:
    """
    Get or create global adapter instance
    Thread-safe singleton pattern

    Args:
        gateway_url: Gateway URL (loads from config if not provided)
        region: AWS region (loads from config if not provided)

    Returns:
        MCPAdapter instance
    """
    global _adapter

    async with _adapter_lock:
        if _adapter is None:
            # Load config if not provided
            if gateway_url is None or region is None:
                from src.adapters.gateway_config import load_gateway_config
                config = load_gateway_config()
                gateway_url = gateway_url or config['gateway_url']
                region = region or config.get('region', 'us-west-2')

            _adapter = MCPAdapter(gateway_url, region)
            logger.info("🌐 Global MCP adapter initialized")

        return _adapter


async def reset_adapter():
    """
    Reset global adapter (useful for testing or cache clearing)
    """
    global _adapter
    async with _adapter_lock:
        if _adapter:
            _adapter._tools_cache = None  # Clear cache
            _adapter = None
            logger.info("Global MCP adapter reset")


# ============================================================================
# Convenience Functions
# ============================================================================

async def quick_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Quick tool call using global adapter

    Args:
        tool_name: Tool to call
        arguments: Tool arguments

    Returns:
        Tool result
    """
    adapter = await get_adapter()
    return await adapter.call_tool(tool_name, arguments)


async def list_available_tools() -> List[str]:
    """
    Get list of available tool names

    Returns:
        List of tool names
    """
    adapter = await get_adapter()
    tools = await adapter.list_tools()
    return [tool.name for tool in tools]
