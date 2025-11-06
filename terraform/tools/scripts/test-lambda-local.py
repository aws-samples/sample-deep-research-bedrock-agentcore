#!/usr/bin/env python3
"""
Local Lambda function tester
Tests Tavily Lambda without deploying to AWS
"""
import json
import sys
import os
from pathlib import Path

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent / "lambdas" / "tavily"
sys.path.insert(0, str(lambda_dir))

# Mock AWS context
class MockContext:
    def __init__(self):
        self.function_name = "test-tavily"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:us-west-2:123456789:function:test-tavily"
        self.memory_limit_in_mb = 512
        self.aws_request_id = "test-request-id"
        self.log_group_name = "/aws/lambda/test-tavily"
        self.log_stream_name = "test-stream"

        # Mock client context for tool name
        self.client_context = type('obj', (object,), {
            'custom': {'bedrockAgentCoreToolName': 'gateway___tavily_search'}
        })


def test_tavily_search():
    """Test tavily_search function"""
    print("🧪 Testing tavily_search...")
    print("=" * 60)

    # Import after path setup
    import lambda_function

    # Mock event (Gateway unwraps tool arguments)
    event = {
        'query': 'Claude AI anthropic',
        'search_depth': 'basic',
        'topic': 'general'
    }

    context = MockContext()

    print(f"Event: {json.dumps(event, indent=2)}")
    print()

    # Note: This will fail without TAVILY_API_KEY
    if not os.getenv('TAVILY_API_KEY'):
        print("⚠️  TAVILY_API_KEY not set. Set it to test API calls:")
        print("   export TAVILY_API_KEY='your-key-here'")
        print()
        print("Testing error handling...")

    result = lambda_function.lambda_handler(event, context)

    print("Result:")
    print(json.dumps(result, indent=2))
    print()

    if result['statusCode'] == 200:
        print("✅ Test passed!")
        body = json.loads(result['body'])
        if 'content' in body:
            content_text = body['content'][0]['text']
            content_data = json.loads(content_text)
            print(f"Results count: {content_data.get('results_count', 0)}")
    else:
        print("❌ Test returned error (expected without API key)")

    print("=" * 60)


def test_tavily_extract():
    """Test tavily_extract function"""
    print("\n🧪 Testing tavily_extract...")
    print("=" * 60)

    import lambda_function

    event = {
        'urls': 'https://www.anthropic.com',
        'extract_depth': 'basic'
    }

    context = MockContext()
    context.client_context.custom['bedrockAgentCoreToolName'] = 'gateway___tavily_extract'

    print(f"Event: {json.dumps(event, indent=2)}")
    print()

    result = lambda_function.lambda_handler(event, context)

    print("Result:")
    print(json.dumps(result, indent=2))
    print()

    if result['statusCode'] == 200:
        print("✅ Test passed!")
    else:
        print("❌ Test returned error (expected without API key)")

    print("=" * 60)


if __name__ == "__main__":
    print("🚀 Tavily Lambda Local Testing")
    print("=" * 60)
    print()

    # Check if API key is set
    if os.getenv('TAVILY_API_KEY'):
        print("✅ TAVILY_API_KEY found")
    else:
        print("⚠️  TAVILY_API_KEY not set (tests will fail API calls)")

    print()

    try:
        test_tavily_search()
        test_tavily_extract()

        print("\n✅ All tests completed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
