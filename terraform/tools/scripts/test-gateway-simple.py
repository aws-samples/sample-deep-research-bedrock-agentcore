#!/usr/bin/env python3
"""
Simple Gateway Test - List Tools Only

Quick test to verify Gateway is accessible and list available tools.
Uses AWS SigV4 authentication for AgentCore Gateway.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path for imports
# Script location: terraform/tools/scripts/test-gateway-simple.py
# Project root: ../../../ (go up 3 levels)
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print("❌ MCP not installed.")
    print("   Install with: pip install mcp")
    sys.exit(1)

try:
    from src.utils.gateway_auth import get_sigv4_auth, get_gateway_region_from_url
except ImportError as e:
    print(f"❌ Failed to import gateway_auth: {e}")
    print("   Make sure src/utils/gateway_auth.py exists")
    sys.exit(1)


async def quick_test(gateway_url: str):
    """Quick test - just list tools with SigV4 auth"""
    print(f"🔗 Connecting to: {gateway_url}")
    print("=" * 60)

    try:
        # Extract region from URL
        region = get_gateway_region_from_url(gateway_url)
        print(f"📍 Region: {region}")

        # Get SigV4 auth
        auth = get_sigv4_auth(region=region)
        print("🔐 Using AWS SigV4 authentication")

        # Connect to MCP server with SigV4 auth
        async with streamablehttp_client(
            url=gateway_url,
            auth=auth,
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the session
                await session.initialize()
                print("✅ Connected!")

                # List tools
                tools_result = await session.list_tools()
                tools = tools_result.tools

                print(f"\n📋 Available Tools: {len(tools)}\n")

                for idx, tool in enumerate(tools, 1):
                    print(f"{idx:2d}. {tool.name}")

                return tools

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    # Try to load from config
    config_file = Path(__file__).parent.parent / "gateway_config.json"

    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            gateway_url = config.get('gateway_url')
            print(f"📄 Loaded from config: {config_file.name}")
    else:
        gateway_url = input("Gateway URL: ").strip()

    if not gateway_url:
        print("❌ No URL provided")
        return

    await quick_test(gateway_url)


if __name__ == "__main__":
    asyncio.run(main())
