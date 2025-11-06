#!/usr/bin/env python3
"""
Test Gateway Tools using MCP Client with SigV4 Auth

This script connects to the deployed AgentCore Gateway and:
1. Lists all available tools
2. Tests each tool with sample queries

Uses AWS SigV4 authentication for AgentCore Gateway.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import TextContent
except ImportError:
    print("❌ MCP not installed. Install with: pip install mcp")
    sys.exit(1)

try:
    from src.utils.gateway_auth import get_sigv4_auth, get_gateway_region_from_url
except ImportError as e:
    print(f"❌ Failed to import gateway_auth: {e}")
    print("   Make sure src/utils/gateway_auth.py exists")
    sys.exit(1)


async def create_gateway_session(gateway_url: str):
    """Create an authenticated MCP session with the Gateway"""
    # Extract region from URL
    region = get_gateway_region_from_url(gateway_url)

    # Get SigV4 auth
    auth = get_sigv4_auth(region=region)

    # Connect to MCP server with SigV4 auth
    return streamablehttp_client(url=gateway_url, auth=auth)


async def test_gateway_connection(gateway_url: str):
    """Test basic gateway connection"""
    print(f"🔗 Connecting to Gateway: {gateway_url}")

    try:
        async with await create_gateway_session(gateway_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the session
                result = await session.initialize()
                print(f"✅ Connected: {result.server_info.name if result.server_info else 'Gateway'}")

                return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def list_gateway_tools(gateway_url: str):
    """List all available tools from the Gateway"""
    print("\n📋 Listing Gateway Tools...")
    print("=" * 60)

    try:
        async with await create_gateway_session(gateway_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the session
                await session.initialize()

                # List all tools
                tools_result = await session.list_tools()
                tools = tools_result.tools

                print(f"\n✅ Found {len(tools)} tools:\n")

                for idx, tool in enumerate(tools, 1):
                    print(f"{idx}. {tool.name}")
                    print(f"   Description: {tool.description}")

                    # Show input schema
                    if tool.inputSchema:
                        schema = tool.inputSchema
                        if 'properties' in schema:
                            props = schema['properties']
                            required = schema.get('required', [])
                            print(f"   Parameters:")
                            for param_name, param_info in props.items():
                                req_marker = "* " if param_name in required else "  "
                                param_type = param_info.get('type', 'string')
                                param_desc = param_info.get('description', '')
                                print(f"     {req_marker}{param_name} ({param_type}): {param_desc}")
                    print()

                return tools

    except Exception as e:
        print(f"❌ Failed to list tools: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_tool_call(gateway_url: str, tool_name: str, params: dict):
    """Test calling a specific tool"""
    print(f"\n🧪 Testing tool: {tool_name}")
    print(f"   Parameters: {json.dumps(params, indent=2)}")
    print("-" * 60)

    try:
        async with await create_gateway_session(gateway_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the session
                await session.initialize()

                # Call the tool
                result = await session.call_tool(tool_name, params)

                print("✅ Tool call successful!")

                # Parse result
                if result.content:
                    for content_item in result.content:
                        if isinstance(content_item, TextContent):
                            print(f"\n📄 Response:\n{content_item.text[:500]}...")
                        else:
                            print(f"\n📄 Response:\n{content_item}")
                else:
                    print(f"\n📄 Response:\n{result}")

                return result

    except Exception as e:
        print(f"❌ Tool call failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_comprehensive_test(gateway_url: str):
    """Run comprehensive Gateway test suite"""
    print("=" * 60)
    print("🚀 Gateway Comprehensive Test Suite")
    print("=" * 60)

    # Test 1: Connection
    connected = await test_gateway_connection(gateway_url)
    if not connected:
        print("\n❌ Connection test failed. Exiting.")
        return

    # Test 2: List tools
    tools = await list_gateway_tools(gateway_url)
    if not tools:
        print("\n❌ No tools found. Exiting.")
        return

    # Test 3: Sample tool calls
    print("\n" + "=" * 60)
    print("🧪 Running Sample Tool Tests")
    print("=" * 60)

    test_cases = [
        {
            "tool": "wikipedia_search",
            "params": {"query": "Artificial Intelligence"}
        },
        {
            "tool": "ddg_search",
            "params": {"query": "Python programming"}
        },
        {
            "tool": "tavily_search",
            "params": {"query": "Claude AI", "search_depth": "basic"}
        },
        {
            "tool": "stock_quote",
            "params": {"symbol": "AAPL"}
        },
        {
            "tool": "arxiv_search",
            "params": {"query": "machine learning"}
        }
    ]

    successful = 0
    failed = 0

    for test_case in test_cases:
        tool_name = test_case["tool"]
        params = test_case["params"]

        # Check if tool exists
        tool_exists = any(t.name == tool_name for t in tools)
        if not tool_exists:
            print(f"\n⚠️  Skipping {tool_name} (not available)")
            continue

        result = await test_tool_call(gateway_url, tool_name, params)

        if result:
            successful += 1
        else:
            failed += 1

        # Small delay between tests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📋 Total tools available: {len(tools)}")


async def main():
    """Main entry point"""

    # Check if gateway_config.json exists
    config_file = Path(__file__).parent.parent / "gateway_config.json"

    if config_file.exists():
        print(f"📄 Loading gateway config from: {config_file}")
        with open(config_file, 'r') as f:
            config = json.load(f)
            gateway_url = config.get('gateway_url')
    else:
        # Manual input
        print("⚠️  gateway_config.json not found")
        gateway_url = input("Enter Gateway URL: ").strip()

    if not gateway_url:
        print("❌ No Gateway URL provided")
        return

    # Run tests
    await run_comprehensive_test(gateway_url)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
