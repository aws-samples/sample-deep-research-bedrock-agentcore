"""
Individual Node Testing Script

Test each workflow node independently with Gateway tools.
Usage:
    python tests/test_nodes_individually.py topic_analysis
    python tests/test_nodes_individually.py aspect_analysis
    python tests/test_nodes_individually.py research_agent
    python tests/test_nodes_individually.py reference_preparation
    python tests/test_nodes_individually.py all
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add research-agent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "research-agent"))

from dotenv import load_dotenv
load_dotenv()

# Initialize logging
from src.utils.logger import setup_logger
logger = setup_logger(name="test_nodes", level="INFO")


async def test_topic_analysis():
    """Test topic_analysis_node independently"""
    print("\n" + "="*80)
    print("TEST: topic_analysis_node")
    print("="*80)

    from src.nodes.topic_analysis import topic_analysis_node
    from src.config.research_config import ResearchConfig

    # Create mock state
    state = {
        "topic": "Amazon Stock Valuation and Vision",
        "research_session_id": "test_session_topic_analysis",
        "research_config": ResearchConfig(
            research_type="finance",
            research_depth="quick"
        ).to_dict()
    }

    print(f"📋 Topic: {state['topic']}")
    print(f"🔬 Research Type: basic_web")

    # Run node
    result = await topic_analysis_node(state)

    # Display results
    print(f"\n✅ Dimensions identified: {len(result.get('dimensions', []))}")
    for idx, dim in enumerate(result.get('dimensions', []), 1):
        print(f"   {idx}. {dim}")

    return result


async def test_aspect_analysis():
    """Test aspect_analysis_node independently"""
    print("\n" + "="*80)
    print("TEST: aspect_analysis_node")
    print("="*80)

    from src.nodes.aspect_analysis import aspect_analysis_node
    from src.config.research_config import ResearchConfig

    # Create mock state for one dimension
    state = {
        "dimension": "Technical Architecture and Implementation",
        "topic": "MCP server implementation best practices",
        "research_session_id": "test_session_aspect_analysis",
        "reference_materials": [],
        "research_config": ResearchConfig(
            research_type="basic_web",
            research_depth="quick"
        ).to_dict()
    }

    print(f"📋 Topic: {state['topic']}")
    print(f"📊 Dimension: {state['dimension']}")

    # Run node
    result = await aspect_analysis_node(state)

    # Display results
    aspects_by_dim = result.get('original_aspects_by_dimension', {})
    for dim, aspects in aspects_by_dim.items():
        print(f"\n✅ Aspects for '{dim}': {len(aspects)}")
        for idx, aspect in enumerate(aspects, 1):
            if isinstance(aspect, dict):
                print(f"   {idx}. {aspect.get('name', 'N/A')}")
                print(f"      Reasoning: {aspect.get('reasoning', 'N/A')[:100]}...")
            else:
                print(f"   {idx}. {aspect}")

    return result


async def test_research_agent_financial():
    """Test research_agent_node with FINANCIAL research type"""
    print("\n" + "="*80)
    print("TEST: research_agent_node (FINANCIAL)")
    print("="*80)

    from src.nodes.research_agent import research_agent_node
    from src.config.research_config import ResearchConfig

    # Create mock state for financial research
    aspect = {
        "name": "Current Stock Valuation and Price Targets",
        "reasoning": "Analyze Amazon's current stock price, analyst estimates, and valuation metrics",
        "key_questions": [
            "What is Amazon's current stock price and recent performance?",
            "What are analyst price targets and recommendations?",
            "What are key valuation metrics (P/E, EPS, etc.)?"
        ]
    }

    state = {
        "aspect": aspect,
        "dimension": "Financial Performance",
        "topic": "Amazon Stock Analysis",
        "research_session_id": "test_session_financial",
        "user_id": "test_user_123",  # Add user_id
        "reference_materials": [],
        "aspects_by_dimension": {
            "Financial Performance": [aspect]
        },
        "research_config": ResearchConfig(
            research_type="financial",  # ⚠️  FINANCIAL type!
            research_depth="quick",
            agent_max_iterations=15
        ).to_dict(),
        "research_context": ""
    }

    print(f"📋 Topic: {state['topic']}")
    print(f"💰 Research Type: FINANCIAL")
    print(f"📊 Dimension: {state['dimension']}")
    print(f"🔍 Aspect: {aspect['name']}")
    print(f"❓ Questions: {len(aspect['key_questions'])}")

    # Run node
    result = await research_agent_node(state)

    # Display results
    research_by_aspect = result.get('research_by_aspect', {})
    for aspect_key, research in research_by_aspect.items():
        print(f"\n✅ Research completed for: {aspect_key}")
        if isinstance(research, dict):
            print(f"   Title: {research.get('title', 'N/A')}")
            print(f"   Word count: {research.get('word_count', 0)}")
            content = research.get('content', '')
            print(f"   Content preview: {content[:300]}...")
        else:
            print(f"   Content length: {len(research)} chars")

    return result


async def test_research_agent():
    """Test research_agent_node independently"""
    print("\n" + "="*80)
    print("TEST: research_agent_node")
    print("="*80)

    from src.nodes.research_agent import research_agent_node
    from src.config.research_config import ResearchConfig

    # Create mock state for one aspect
    aspect = {
        "name": "Protocol Design and Standards",
        "reasoning": "Understanding the core protocol specifications and design principles",
        "key_questions": [
            "What are the key protocol specifications?",
            "How does MCP ensure interoperability?"
        ]
    }

    state = {
        "aspect": aspect,
        "dimension": "Technical Architecture",
        "topic": "MCP server implementation best practices",
        "research_session_id": "test_session_research_agent",
        "user_id": "test_user_123",  # Add user_id
        "reference_materials": [],
        "aspects_by_dimension": {
            "Technical Architecture": [aspect]
        },
        "research_config": ResearchConfig(
            research_type="basic_web",
            research_depth="quick",
            agent_max_iterations=15  # Limit iterations for testing
        ).to_dict(),
        "research_context": ""
    }

    print(f"📋 Topic: {state['topic']}")
    print(f"📊 Dimension: {state['dimension']}")
    print(f"🔍 Aspect: {aspect['name']}")
    print(f"❓ Questions: {len(aspect['key_questions'])}")

    # Run node
    result = await research_agent_node(state)

    # Display results
    research_by_aspect = result.get('research_by_aspect', {})
    for aspect_key, research in research_by_aspect.items():
        print(f"\n✅ Research completed for: {aspect_key}")
        if isinstance(research, dict):
            print(f"   Title: {research.get('title', 'N/A')}")
            print(f"   Word count: {research.get('word_count', 0)}")
            content = research.get('content', '')
            print(f"   Content preview: {content[:300]}...")
        else:
            print(f"   Content length: {len(research)} chars")

    return result


async def test_reference_preparation():
    """Test reference_preparation_node independently"""
    print("\n" + "="*80)
    print("TEST: reference_preparation_node")
    print("="*80)

    from src.nodes.reference_preparation import reference_preparation_node
    from src.config.research_config import ResearchConfig

    # Create mock state with reference materials
    state = {
        "research_session_id": "test_session_reference_prep",
        "dimensions": ["Architecture", "Implementation"],
        "research_context": "",
        "research_config": {
            "research_type": "basic_web",
            "reference_materials": [
                {
                    "type": "url",
                    "url": "https://modelcontextprotocol.io/introduction",
                    "note": "Official MCP introduction"
                }
            ]
        }
    }

    print(f"📚 Reference materials: {len(state['research_config']['reference_materials'])}")

    # Run node
    result = await reference_preparation_node(state)

    # Display results
    materials = result.get('reference_materials', [])
    print(f"\n✅ Processed {len(materials)} reference material(s)")
    for idx, mat in enumerate(materials, 1):
        print(f"\n   {idx}. Type: {mat.get('type', 'N/A')}")
        print(f"      Title: {mat.get('title', 'N/A')}")
        print(f"      Source: {mat.get('source', 'N/A')}")
        summary = mat.get('summary', '')
        if summary:
            print(f"      Summary: {summary[:200]}...")

    return result


async def test_all_nodes():
    """Test all nodes sequentially"""
    print("\n" + "="*80)
    print("TESTING ALL NODES SEQUENTIALLY")
    print("="*80)

    results = {}

    try:
        # Test 1: Topic Analysis
        print("\n[1/4] Testing topic_analysis_node...")
        results['topic_analysis'] = await test_topic_analysis()
        print("✅ topic_analysis_node passed")
    except Exception as e:
        print(f"❌ topic_analysis_node failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        # Test 2: Aspect Analysis
        print("\n[2/4] Testing aspect_analysis_node...")
        results['aspect_analysis'] = await test_aspect_analysis()
        print("✅ aspect_analysis_node passed")
    except Exception as e:
        print(f"❌ aspect_analysis_node failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        # Test 3: Research Agent (this takes longest)
        print("\n[3/4] Testing research_agent_node...")
        results['research_agent'] = await test_research_agent()
        print("✅ research_agent_node passed")
    except Exception as e:
        print(f"❌ research_agent_node failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        # Test 4: Reference Preparation
        print("\n[4/4] Testing reference_preparation_node...")
        results['reference_preparation'] = await test_reference_preparation()
        print("✅ reference_preparation_node passed")
    except Exception as e:
        print(f"❌ reference_preparation_node failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = len([k for k, v in results.items() if v is not None])
    total = 4
    print(f"Passed: {passed}/{total}")
    print("="*80)

    return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Test individual workflow nodes')
    parser.add_argument(
        'node',
        choices=['topic_analysis', 'aspect_analysis', 'research_agent', 'research_agent_financial', 'reference_preparation', 'all'],
        help='Node to test'
    )

    args = parser.parse_args()

    # Check AWS credentials
    import boto3
    try:
        boto3.client('bedrock-runtime', region_name='us-west-2')
        print("✅ AWS credentials configured")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("\nPlease configure AWS credentials:")
        print("  aws configure")
        sys.exit(1)

    # Run selected test
    if args.node == 'all':
        asyncio.run(test_all_nodes())
    elif args.node == 'topic_analysis':
        asyncio.run(test_topic_analysis())
    elif args.node == 'aspect_analysis':
        asyncio.run(test_aspect_analysis())
    elif args.node == 'research_agent':
        asyncio.run(test_research_agent())
    elif args.node == 'research_agent_financial':
        asyncio.run(test_research_agent_financial())
    elif args.node == 'reference_preparation':
        asyncio.run(test_reference_preparation())


if __name__ == "__main__":
    main()
