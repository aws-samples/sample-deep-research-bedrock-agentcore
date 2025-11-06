"""
Adapters for external services
"""
from src.adapters.mcp_adapter import MCPAdapter, get_adapter
from src.adapters.multi_server_adapter import GatewayMCPClient, get_gateway_client

__all__ = ['MCPAdapter', 'get_adapter', 'GatewayMCPClient', 'get_gateway_client']
