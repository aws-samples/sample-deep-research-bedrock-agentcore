#!/usr/bin/env python3
"""
Interactive Gateway Tool Caller

Allows you to select and call Gateway tools interactively with custom parameters.
Uses AWS SigV4 authentication for AgentCore Gateway.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import TextContent, Tool
except ImportError:
    print("❌ MCP not installed. Install with: pip install mcp")
    sys.exit(1)

try:
    from src.utils.gateway_auth import get_sigv4_auth, get_gateway_region_from_url
except ImportError as e:
    print(f"❌ Failed to import gateway_auth: {e}")
    print("   Make sure src/utils/gateway_auth.py exists")
    sys.exit(1)


# Predefined example parameters for common tools
EXAMPLE_PARAMS = {
    "tavily_search": {
        "query": "Latest AI developments",
        "search_depth": "basic"
    },
    "tavily_extract": {
        "urls": "https://www.anthropic.com"
    },
    "wikipedia_search": {
        "query": "Machine Learning"
    },
    "wikipedia_get_article": {
        "title": "Artificial Intelligence",
        "summary_only": False
    },
    "ddg_search": {
        "query": "Python programming best practices"
    },
    "ddg_news": {
        "query": "AI technology",
        "timelimit": "d"
    },
    "google_web_search": {
        "query": "AWS Bedrock documentation"
    },
    "google_image_search": {
        "query": "neural network diagram"
    },
    "arxiv_search": {
        "query": "deep learning"
    },
    "arxiv_get_paper": {
        "paper_ids": "2308.08155"
    },
    "stock_quote": {
        "symbol": "AAPL"
    },
    "stock_history": {
        "symbol": "MSFT",
        "period": "1mo"
    },
    "financial_news": {
        "symbol": "TSLA",
        "count": 5
    },
    "stock_analysis": {
        "symbol": "GOOGL"
    }
}


async def create_gateway_session(gateway_url: str):
    """Create an authenticated MCP session with the Gateway"""
    region = get_gateway_region_from_url(gateway_url)
    auth = get_sigv4_auth(region=region)
    return streamablehttp_client(url=gateway_url, auth=auth)


async def list_tools(gateway_url: str) -> List[Tool]:
    """List all available tools from the Gateway"""
    async with await create_gateway_session(gateway_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools


def extract_tool_name(full_name: str) -> str:
    """Extract tool name from Gateway format: target___tool -> tool"""
    if '___' in full_name:
        return full_name.split('___')[-1]
    return full_name


def display_tools(tools: List[Tool]):
    """Display tools in a numbered list"""
    print("\n" + "=" * 70)
    print("📋 Available Tools:")
    print("=" * 70)

    for idx, tool in enumerate(tools, 1):
        tool_name = extract_tool_name(tool.name)
        print(f"{idx:2d}. {tool_name:30s} - {tool.description[:50]}...")

    print("=" * 70)


def display_tool_schema(tool: Tool):
    """Display detailed schema for a tool"""
    tool_name = extract_tool_name(tool.name)
    print("\n" + "=" * 70)
    print(f"🔧 Tool: {tool_name}")
    print("=" * 70)
    print(f"Description: {tool.description}")

    if tool.inputSchema and 'properties' in tool.inputSchema:
        props = tool.inputSchema['properties']
        required = tool.inputSchema.get('required', [])

        print("\n📝 Parameters:")
        for param_name, param_info in props.items():
            req_marker = "* " if param_name in required else "  "
            param_type = param_info.get('type', 'string')
            param_desc = param_info.get('description', '')
            print(f"  {req_marker}{param_name:20s} ({param_type:10s}) - {param_desc}")

    # Show example parameters if available
    if tool_name in EXAMPLE_PARAMS:
        print("\n💡 Example parameters:")
        print(json.dumps(EXAMPLE_PARAMS[tool_name], indent=2))

    print("=" * 70)


async def call_tool(gateway_url: str, tool_name: str, params: Dict[str, Any]):
    """Call a tool with given parameters"""
    print(f"\n🚀 Calling tool: {tool_name}")
    print(f"Parameters: {json.dumps(params, indent=2)}")
    print("-" * 70)

    try:
        async with await create_gateway_session(gateway_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Call the tool
                result = await session.call_tool(tool_name, params)

                print("✅ Tool call successful!")
                print("=" * 70)

                # Parse and display result
                if result.content:
                    for idx, content_item in enumerate(result.content, 1):
                        if isinstance(content_item, TextContent):
                            print(f"\n📄 Response {idx}:")
                            print(content_item.text)
                        else:
                            print(f"\n📄 Response {idx}:")
                            print(content_item)
                else:
                    print(f"\n📄 Response:")
                    print(result)

                print("=" * 70)
                return result

    except Exception as e:
        print(f"❌ Tool call failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_user_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()


async def interactive_mode(gateway_url: str):
    """Interactive tool calling mode"""
    print("\n" + "=" * 70)
    print("🎯 Interactive Gateway Tool Caller")
    print("=" * 70)
    print("Loading tools from Gateway...")

    # Load tools
    tools = await list_tools(gateway_url)
    if not tools:
        print("❌ No tools available")
        return

    print(f"✅ Loaded {len(tools)} tools")

    while True:
        display_tools(tools)

        print("\nOptions:")
        print("  - Enter tool number (1-{})".format(len(tools)))
        print("  - 'q' to quit")
        print("  - 'r' to refresh tool list")

        choice = get_user_input("\nYour choice").lower()

        if choice == 'q':
            print("👋 Goodbye!")
            break

        if choice == 'r':
            print("🔄 Refreshing tool list...")
            tools = await list_tools(gateway_url)
            continue

        # Validate tool selection
        try:
            tool_idx = int(choice) - 1
            if tool_idx < 0 or tool_idx >= len(tools):
                print("❌ Invalid tool number")
                continue
        except ValueError:
            print("❌ Invalid input")
            continue

        selected_tool = tools[tool_idx]
        tool_name = extract_tool_name(selected_tool.name)

        # Display tool schema
        display_tool_schema(selected_tool)

        # Get parameters
        print("\n🔧 Parameter Input")
        print("Options:")
        print("  1. Use example parameters (if available)")
        print("  2. Enter custom JSON parameters")
        print("  3. Enter parameters interactively")
        print("  0. Back to tool selection")

        param_choice = get_user_input("\nParameter method", "1")

        if param_choice == "0":
            continue

        params = {}

        if param_choice == "1":
            # Use example parameters
            if tool_name in EXAMPLE_PARAMS:
                params = EXAMPLE_PARAMS[tool_name].copy()
                print(f"✅ Using example parameters: {json.dumps(params, indent=2)}")

                # Allow editing
                edit = get_user_input("Edit parameters? (y/n)", "n").lower()
                if edit == 'y':
                    for key, value in params.items():
                        new_value = get_user_input(f"  {key}", str(value))
                        # Try to convert to original type
                        if isinstance(value, bool):
                            params[key] = new_value.lower() in ('true', 'yes', '1')
                        elif isinstance(value, int):
                            params[key] = int(new_value)
                        else:
                            params[key] = new_value
            else:
                print("⚠️  No example parameters available. Enter custom parameters.")
                param_choice = "2"

        if param_choice == "2":
            # Enter JSON parameters
            print("\nEnter parameters as JSON (e.g., {\"query\": \"AI\", \"depth\": \"basic\"})")
            json_str = input("Parameters: ").strip()
            try:
                params = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                continue

        elif param_choice == "3":
            # Interactive parameter entry
            if selected_tool.inputSchema and 'properties' in selected_tool.inputSchema:
                props = selected_tool.inputSchema['properties']
                required = selected_tool.inputSchema.get('required', [])

                print("\nEnter parameter values (press Enter to skip optional parameters):")
                for param_name, param_info in props.items():
                    is_required = param_name in required
                    param_type = param_info.get('type', 'string')
                    param_desc = param_info.get('description', '')

                    prompt = f"  {param_name} ({param_type})"
                    if is_required:
                        prompt += " *REQUIRED*"
                    prompt += f"\n    {param_desc}\n  Value"

                    value = input(f"{prompt}: ").strip()

                    if not value and is_required:
                        print(f"❌ {param_name} is required")
                        params = {}
                        break

                    if value:
                        # Try to convert to correct type
                        if param_type == 'boolean':
                            params[param_name] = value.lower() in ('true', 'yes', '1')
                        elif param_type == 'integer':
                            params[param_name] = int(value)
                        else:
                            params[param_name] = value

                if not params:
                    continue

        # Call the tool
        result = await call_tool(gateway_url, selected_tool.name, params)

        # Ask if user wants to continue
        print("\n")
        continue_choice = get_user_input("Call another tool? (y/n)", "y").lower()
        if continue_choice != 'y':
            print("👋 Goodbye!")
            break


async def quick_call_mode(gateway_url: str, tool_name: str, params: Dict[str, Any]):
    """Quick mode - call tool directly with parameters"""
    print("\n" + "=" * 70)
    print("🎯 Quick Tool Call Mode")
    print("=" * 70)

    # Load tools to validate
    tools = await list_tools(gateway_url)

    # Find the tool (handle both full name and short name)
    matching_tool = None
    for tool in tools:
        short_name = extract_tool_name(tool.name)
        if tool.name == tool_name or short_name == tool_name:
            matching_tool = tool
            break

    if not matching_tool:
        print(f"❌ Tool not found: {tool_name}")
        print(f"\nAvailable tools:")
        for tool in tools:
            print(f"  - {extract_tool_name(tool.name)}")
        return

    # Call the tool
    await call_tool(gateway_url, matching_tool.name, params)


async def main():
    """Main entry point"""
    # Load Gateway URL from config
    config_file = Path(__file__).parent.parent / "gateway_config.json"

    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            gateway_url = config.get('gateway_url')
    else:
        gateway_url = input("Gateway URL: ").strip()

    if not gateway_url:
        print("❌ No Gateway URL provided")
        return

    # Check if running in quick mode (with arguments)
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]

        # Parse parameters from command line
        if len(sys.argv) > 2:
            try:
                params = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                print("❌ Invalid JSON parameters")
                print("Usage: python call-gateway-tool.py <tool_name> '<json_params>'")
                return
        else:
            # Use example parameters if available
            short_name = tool_name.split('___')[-1]
            if short_name in EXAMPLE_PARAMS:
                params = EXAMPLE_PARAMS[short_name]
            else:
                print(f"❌ No example parameters for {tool_name}")
                print("Provide parameters: python call-gateway-tool.py <tool_name> '<json_params>'")
                return

        await quick_call_mode(gateway_url, tool_name, params)
    else:
        # Interactive mode
        await interactive_mode(gateway_url)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
