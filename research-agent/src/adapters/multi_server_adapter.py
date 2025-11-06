"""
MultiServerMCPClient adapter with AWS SigV4 authentication
Replaces MCPAdapter with LangChain's official client
"""
import asyncio
import logging
from typing import Optional, List, Any
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from mcp import ClientSession

from src.utils.gateway_auth import get_sigv4_auth, get_gateway_region_from_url

logger = logging.getLogger(__name__)


class GatewayMCPClient:
    """
    Wrapper around MultiServerMCPClient with AWS SigV4 authentication
    Manages persistent connection to AgentCore Gateway
    """

    def __init__(self, gateway_url: str, region: Optional[str] = None):
        """
        Initialize Gateway MCP Client

        Args:
            gateway_url: AgentCore Gateway URL
            region: AWS region (auto-detected if not provided)
        """
        self.gateway_url = gateway_url

        # Auto-detect region from URL if not provided
        if region is None:
            region = get_gateway_region_from_url(gateway_url)
        self.region = region

        # Get SigV4 auth
        self.auth = get_sigv4_auth(region=self.region)

        # Create connection config with SigV4 auth
        # MultiServerMCPClient expects a dict of connections
        connections = {
            "gateway": {
                "url": gateway_url,
                "transport": "streamable_http",
                # Pass auth as part of connection config
                # Note: This needs to be handled by the underlying transport
            }
        }

        # Initialize MultiServerMCPClient
        self._client = MultiServerMCPClient(connections=connections)
        self._tools_cache: Optional[List[BaseTool]] = None

        logger.info(f"GatewayMCPClient initialized for {gateway_url} (region: {region})")

    async def get_tools(self, force_refresh: bool = False) -> List[BaseTool]:
        """
        Get tools from Gateway with caching

        Args:
            force_refresh: Bypass cache and fetch fresh tools

        Returns:
            List of LangChain tools
        """
        if self._tools_cache and not force_refresh:
            logger.debug(f"Using cached tools ({len(self._tools_cache)} tools)")
            return self._tools_cache

        try:
            from langchain_mcp_adapters.tools import load_mcp_tools
            import httpx

            # Create httpx client factory with SigV4 auth
            def create_auth_client(
                headers: dict[str, str] | None = None,
                timeout: httpx.Timeout | None = None,
                auth: httpx.Auth | None = None,
            ) -> httpx.AsyncClient:
                """Create httpx client with SigV4 authentication"""
                # Use our SigV4 auth instead of provided auth
                return httpx.AsyncClient(
                    headers=headers,
                    timeout=timeout or httpx.Timeout(60.0),
                    auth=self.auth  # Inject SigV4 auth
                )

            # Create connection config with SigV4 auth via client factory
            connection_config = {
                "url": self.gateway_url,
                "transport": "streamable_http",
                "httpx_client_factory": create_auth_client  # Inject SigV4 via factory
            }

            # Load tools with connection config
            # This way each tool call will create a new session automatically
            tools = await load_mcp_tools(
                session=None,
                connection=connection_config,
                server_name="gateway"
            )

            # Convert tool names to simple format (remove target___ prefix)
            # Gateway format: "target___tool_name" -> "tool_name"
            converted_tools = []
            for tool in tools:
                simple_name = tool.name.split('___')[-1] if '___' in tool.name else tool.name
                simple_name = simple_name.replace('-', '_')

                # Recreate tool with simplified name
                from langchain_core.tools import StructuredTool
                new_tool = StructuredTool(
                    name=simple_name,
                    description=tool.description,
                    coroutine=tool.coroutine if hasattr(tool, 'coroutine') else None,
                    args_schema=tool.args_schema if hasattr(tool, 'args_schema') else None
                )
                converted_tools.append(new_tool)
                logger.debug(f"Converted tool: {tool.name} -> {simple_name}")

            self._tools_cache = converted_tools
            logger.info(f"📦 Loaded {len(converted_tools)} tools from Gateway")
            return converted_tools

        except Exception as e:
            logger.error(f"Failed to get tools: {e}")
            raise

    @asynccontextmanager
    async def session(self) -> ClientSession:
        """
        Get an MCP session with SigV4 authentication

        Yields:
            ClientSession for Gateway operations
        """
        # We need to inject SigV4 auth into the streamable_http connection
        # This requires creating the connection manually
        from mcp.client.streamable_http import streamablehttp_client

        logger.debug(f"🔌 Creating Gateway session with SigV4 auth: {self.gateway_url}")

        try:
            # Create transport with SigV4 auth
            # streamablehttp_client returns a context manager, don't await it
            async with streamablehttp_client(
                url=self.gateway_url,
                auth=self.auth
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    logger.debug("✅ MCP session initialized")
                    yield session
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Gateway is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with self.session() as session:
                result = await session.list_tools()
                logger.info(f"✅ Gateway health check passed ({len(result.tools)} tools available)")
                return True
        except Exception as e:
            logger.warning(f"Gateway health check failed: {e}")
            return False

    def clear_cache(self):
        """Clear tools cache"""
        self._tools_cache = None
        logger.debug("Tools cache cleared")


# ============================================================================
# Global Client Management
# ============================================================================

_client: Optional[GatewayMCPClient] = None
_client_lock = asyncio.Lock()


async def get_gateway_client(gateway_url: str = None, region: str = None) -> GatewayMCPClient:
    """
    Get or create global Gateway client instance
    Thread-safe singleton pattern

    Args:
        gateway_url: Gateway URL (loads from config if not provided)
        region: AWS region (loads from config if not provided)

    Returns:
        GatewayMCPClient instance
    """
    global _client

    async with _client_lock:
        if _client is None:
            # Load config if not provided
            if gateway_url is None or region is None:
                from src.adapters.gateway_config import load_gateway_config
                config = load_gateway_config()
                gateway_url = gateway_url or config['gateway_url']
                region = region or config.get('region', 'us-west-2')

            _client = GatewayMCPClient(gateway_url, region)
            logger.info("🌐 Global Gateway MCP client initialized")

        return _client


async def reset_client():
    """
    Reset global client (useful for testing or cache clearing)
    """
    global _client
    async with _client_lock:
        if _client:
            _client.clear_cache()
            _client = None
            logger.info("Global Gateway MCP client reset")


# ============================================================================
# Convenience Functions
# ============================================================================

async def get_gateway_tools(force_refresh: bool = False) -> List[BaseTool]:
    """
    Get tools from Gateway using global client

    Args:
        force_refresh: Bypass cache

    Returns:
        List of LangChain tools
    """
    client = await get_gateway_client()
    return await client.get_tools(force_refresh=force_refresh)


async def check_gateway_health() -> bool:
    """
    Check Gateway health using global client

    Returns:
        True if healthy, False otherwise
    """
    client = await get_gateway_client()
    return await client.health_check()
