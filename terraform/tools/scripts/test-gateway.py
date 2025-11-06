#!/usr/bin/env python3
"""
Test Gateway connection without full Agent Runtime
Simple MCP client with SigV4 authentication
"""
import json
import sys
import asyncio
import boto3
from pathlib import Path

try:
    from mcp import ClientSession
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    import httpx
except ImportError:
    print("❌ Required packages not installed. Install with:")
    print("   pip install mcp boto3 httpx")
    sys.exit(1)


class SigV4HTTPXAuth(httpx.Auth):
    """HTTPX Auth class that signs requests with AWS SigV4"""

    def __init__(self, credentials, service: str, region: str):
        self.credentials = credentials
        self.service = service
        self.region = region
        self.signer = SigV4Auth(credentials, service, region)

    def auth_flow(self, request):
        """Signs the request with SigV4"""
        headers = dict(request.headers)
        headers.pop("connection", None)

        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers,
        )

        self.signer.add_auth(aws_request)
        request.headers.update(dict(aws_request.headers))

        yield request


async def test_gateway(gateway_url: str, region: str):
    """Test Gateway connection and list tools"""
    print(f"🔗 Connecting to Gateway: {gateway_url}")
    print(f"📍 Region: {region}")
    print()

    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()

    if not credentials:
        print("❌ AWS credentials not found")
        sys.exit(1)

    print(f"✅ AWS credentials obtained")
    print(f"   Account: {boto3.client('sts').get_caller_identity()['Account']}")
    print()

    # Create HTTP client with SigV4
    auth = SigV4HTTPXAuth(credentials, 'bedrock-agentcore', region)

    async with httpx.AsyncClient(auth=auth, timeout=30.0) as http_client:
        try:
            # MCP initialize request
            print("🔌 Initializing MCP session...")

            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }

            response = await http_client.post(
                gateway_url,
                json=init_request,
                headers={"Content-Type": "application/json"}
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ Failed to initialize: {response.text}")
                return

            init_result = response.json()
            print("✅ MCP session initialized")
            print(f"   Server: {init_result.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
            print()

            # List tools
            print("📋 Listing available tools...")

            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            response = await http_client.post(
                gateway_url,
                json=list_tools_request,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                print(f"❌ Failed to list tools: {response.text}")
                return

            tools_result = response.json()
            tools = tools_result.get('result', {}).get('tools', [])

            print(f"✅ Found {len(tools)} tools:")
            print()

            for tool in tools:
                print(f"  🔧 {tool['name']}")
                print(f"     {tool.get('description', 'No description')}")
                print()

            # Test a tool call
            if tools:
                print("🧪 Testing tool call: tavily_search")

                call_tool_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "tavily_search",
                        "arguments": {
                            "query": "Claude AI Anthropic",
                            "search_depth": "basic"
                        }
                    }
                }

                response = await http_client.post(
                    gateway_url,
                    json=call_tool_request,
                    headers={"Content-Type": "application/json"}
                )

                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print("✅ Tool call successful!")

                    content = result.get('result', {}).get('content', [])
                    if content:
                        tool_output = content[0].get('text', '')
                        # Parse and pretty print
                        try:
                            output_data = json.loads(tool_output)
                            print(f"   Results: {output_data.get('results_count', 0)}")
                            if output_data.get('results'):
                                first_result = output_data['results'][0]
                                print(f"   First result: {first_result.get('title', 'N/A')[:60]}...")
                        except:
                            print(f"   Output (first 200 chars): {tool_output[:200]}...")
                else:
                    print(f"❌ Tool call failed: {response.text}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


def load_gateway_config():
    """Load gateway config from deployment"""
    config_path = Path(__file__).parent.parent / "gateway_config.json"

    if not config_path.exists():
        print("❌ gateway_config.json not found!")
        print("   Run deployment first: ./scripts/deploy.sh")
        sys.exit(1)

    with open(config_path) as f:
        return json.load(f)


def main():
    print("🚀 Gateway Connection Test")
    print("=" * 60)
    print()

    config = load_gateway_config()

    gateway_url = config.get('gateway_url')
    region = config.get('region', 'us-west-2')

    if not gateway_url:
        print("❌ Gateway URL not found in config")
        sys.exit(1)

    asyncio.run(test_gateway(gateway_url, region))

    print()
    print("=" * 60)
    print("✅ Test complete!")


if __name__ == "__main__":
    main()
