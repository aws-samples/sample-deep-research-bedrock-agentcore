#!/usr/bin/env python3
"""
Simple Gateway Test - List Tools Only

Quick test to verify Gateway is accessible and list available tools.
Uses AWS SigV4 authentication for AgentCore Gateway.
"""

import asyncio
import json
import sys
import re
from pathlib import Path

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print("❌ MCP not installed.")
    print("   Install with: pip install mcp")
    sys.exit(1)

try:
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
except ImportError:
    print("❌ boto3 not installed.")
    print("   Install with: pip install boto3")
    sys.exit(1)


def get_gateway_region_from_url(url: str) -> str:
    """Extract AWS region from Gateway URL"""
    match = re.search(r'\.([a-z]{2}-[a-z]+-\d)\.', url)
    if match:
        return match.group(1)
    # Default to us-west-2
    return 'us-west-2'


def get_sigv4_auth(region: str = 'us-west-2'):
    """Get AWS SigV4 authentication for bedrock-agentcore-gateway service"""
    session = boto3.Session()
    credentials = session.get_credentials()

    class SigV4AuthWrapper:
        def __init__(self, credentials, region):
            self.credentials = credentials
            self.region = region

        def __call__(self, request):
            # Convert to AWSRequest for signing
            headers = dict(request.headers)

            # Remove 'connection' header - causes signature mismatch
            headers.pop("connection", None)

            aws_request = AWSRequest(
                method=request.method,
                url=str(request.url),
                data=request.content,
                headers=headers
            )

            # Sign the request
            SigV4Auth(self.credentials, 'bedrock-agentcore', self.region).add_auth(aws_request)

            # Update original request headers
            request.headers.update(dict(aws_request.headers))
            return request

    return SigV4AuthWrapper(credentials, region)


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
    # Try to load from config (check multiple locations)
    # 1. Try terraform/tools/gateway_config.json
    config_file = Path(__file__).parent.parent / "gateway_config.json"

    # 2. Try project root (3 levels up from script)
    if not config_file.exists():
        config_file = Path(__file__).parent.parent.parent.parent / "gateway_config.json"

    gateway_url = None
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            gateway_url = config.get('gateway_url')
            print(f"📄 Loaded from config: {config_file}")

    if not gateway_url:
        gateway_url = input("Gateway URL: ").strip()

    if not gateway_url:
        print("❌ No URL provided")
        return

    await quick_test(gateway_url)


if __name__ == "__main__":
    asyncio.run(main())
