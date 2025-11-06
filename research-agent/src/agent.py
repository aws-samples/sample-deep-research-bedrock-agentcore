#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Research Agent - AgentCore Runtime
Dimensional research workflow with LangGraph
"""
import sys
import os
import json
import time
import logging
import asyncio
import queue
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.environ['PYTHONPATH'] = current_dir + ':' + os.environ.get('PYTHONPATH', '')

# Load environment variables from .env if exists
env_file = os.path.join(current_dir, '.env')
if os.path.exists(env_file):
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except Exception:
        pass  # Skip if .env not available

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from src.workflow import create_workflow
from src.config.research_config import get_research_config, DEPTH_CONFIGS
from src.utils.logger import setup_logger

# Set UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='ignore')

# Initialize logging (INFO level for research logs, WARNING for AWS SDK)
# Set up root logger first so all child loggers inherit the configuration
root_logger = setup_logger(name="", level="INFO")  # Root logger
logger = setup_logger(name="research_agent", level="INFO")

# Reduce AWS SDK logging noise
import logging
boto3_logger = logging.getLogger('boto3')
boto3_logger.setLevel(logging.WARNING)

botocore_logger = logging.getLogger('botocore')
botocore_logger.setLevel(logging.WARNING)

# Also reduce other noisy loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('mcp').setLevel(logging.WARNING)

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Global workflow instance
workflow = None

def initialize_workflow():
    """Initialize workflow once"""
    global workflow
    if workflow is None:
        print("Initializing Deep Research workflow...")
        workflow = create_workflow()
        print("✅ Workflow initialized successfully")
    return workflow


class DeepResearchAgent:
    """Deep Research Agent with dimensional analysis"""

    def __init__(self):
        self.workflow = None

    def get_workflow(self):
        """Get or create workflow instance"""
        if self.workflow is None:
            self.workflow = initialize_workflow()
        return self.workflow

    async def run_research(self, topic, research_config, session_id, context=None):
        """
        Execute research workflow

        Args:
            topic: Research topic
            research_config: Research configuration dict
            session_id: Session ID for tracking (from BFF/caller)
            context: Additional context (user_id, etc.)
        """
        start_time = time.time()

        # Get workflow instance
        workflow_instance = self.get_workflow()

        # Configure with session_id for memory/checkpointing
        # Note: recursion_limit here is for the main workflow graph
        # Individual research agents have their own limits set in research_agent.py
        # Use user_id from context as actor_id for proper memory isolation
        actor_id = context.get("user_id", "anonymous") if context else "anonymous"

        config = {
            "configurable": {
                "thread_id": session_id,
                "actor_id": actor_id,  # Use actual user_id for memory isolation
                "session_id": session_id  # Research session ID
            },
            "run_name": "deep_research",
            "tags": [research_config.get("research_type", "basic_web")],
            "metadata": {
                "session_id": session_id,
                "user_id": actor_id,
                "research_type": research_config.get("research_type"),
                "research_depth": research_config.get("research_depth"),
            },
            "recursion_limit": 50  # For main workflow graph (not individual agents)
        }

        # Prepare input - pass session_id and user_id from caller to workflow
        input_state = {
            "topic": topic,
            "research_config": research_config,
            "workflow_start_time": start_time,
            "bff_session_id": session_id,  # Pass BFF session_id to workflow
            "user_id": actor_id  # Pass user_id for event tracking
        }

        # Yield initial status
        yield {
            "type": "status",
            "session_id": session_id,
            "status": "processing",
            "current_stage": "initialize_session",
            "message": f"Starting research: {topic}"
        }

        try:
            # Execute workflow (streaming)
            final_result = None

            logger.info(f"[DEBUG] Starting workflow.astream() - session: {session_id}")

            async for output in workflow_instance.astream(input_state, config):
                logger.info(f"[DEBUG] Workflow stream yielded output - session: {session_id}, keys: {list(output.keys())}")

                # Extract node name and state
                for node_name, state in output.items():
                    if node_name == "__end__":
                        continue

                    # Skip if state is None (aggregator nodes)
                    if state is None:
                        logger.info(f"[DEBUG] Node {node_name} returned None state (aggregator) - session: {session_id}")
                        continue

                    # Store the latest state as final result
                    final_result = state

                    logger.info(f"[DEBUG] Processing node: {node_name} - session: {session_id}")

                    # Yield progress update
                    yield {
                        "type": "progress",
                        "session_id": session_id,
                        "current_stage": node_name,
                        "state": {
                            "dimensions": state.get("dimensions", []),
                            "aspects_by_dimension": state.get("aspects_by_dimension", {}),
                            "research_by_aspect": state.get("research_by_aspect", {}),
                        }
                    }

            # Use the final state from stream (no duplicate invoke!)
            if final_result is None:
                final_result = {}

            elapsed = time.time() - start_time

            yield {
                "type": "complete",
                "session_id": session_id,
                "status": "completed",
                "elapsed_time": elapsed,
                "result": {
                    "topic": final_result.get("topic"),
                    "dimensions": final_result.get("dimensions", []),
                    "aspects_by_dimension": final_result.get("aspects_by_dimension", {}),
                    "research_by_aspect": final_result.get("research_by_aspect", {}),
                    "report_file": final_result.get("report_file"),
                    "dimension_documents": final_result.get("dimension_documents", {}),
                }
            }

        except Exception as e:
            import traceback

            # Check if this is a cancellation exception
            from src.utils.cancellation import ResearchCancelledException

            if isinstance(e, ResearchCancelledException):
                # Research was cancelled by user - update status and return gracefully
                logger.info(f"Research cancelled by user for session {session_id}")

                # Update status to cancelled
                from src.utils.status_updater import get_status_updater
                status_updater = get_status_updater(session_id)
                if status_updater:
                    status_updater.update(
                        status='cancelled',
                        completed_at=datetime.now().isoformat()
                    )

                yield {
                    "type": "cancelled",
                    "session_id": session_id,
                    "status": "cancelled",
                    "message": "Research cancelled by user"
                }
            else:
                # Regular error - mark as failed
                logger.error(f"Research workflow failed for session {session_id}: {str(e)}")
                logger.error(traceback.format_exc())

                # Update status in DynamoDB
                from src.utils.status_updater import get_status_updater
                status_updater = get_status_updater(session_id)
                if status_updater:
                    status_updater.update(
                        status='failed',
                        error=str(e),
                        completed_at=datetime.now().isoformat()
                    )

                yield {
                    "type": "error",
                    "session_id": session_id,
                    "status": "failed",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }


# Global agent instance
agent_instance = None


@app.entrypoint
async def deep_research_agent(payload):
    """
    AgentCore Runtime entrypoint

    Payload format:
    {
        "topic": "Research topic",
        "research_config": {
            "research_type": "basic_web",
            "research_depth": "balanced",
            "research_context": "optional context"
        },
        "session_id": "unique-session-id",
        "user_id": "optional-user-id"
    }
    """
    global agent_instance

    # Extract parameters
    topic = payload.get("topic")
    research_config = payload.get("research_config", {})
    # Accept both bff_session_id (from workflow) and session_id (legacy)
    session_id = payload.get("bff_session_id") or payload.get("session_id")
    user_id = payload.get("user_id")

    # Validate required fields
    if not topic:
        yield {
            "type": "error",
            "error": "Missing required field: topic"
        }
        return

    if not session_id:
        yield {
            "type": "error",
            "error": "Missing required field: session_id"
        }
        return

    # Initialize agent
    if agent_instance is None:
        agent_instance = DeepResearchAgent()

    # Build research config
    research_type = research_config.get("research_type")
    if not research_type:
        yield {
            "type": "error",
            "error": "Missing required field: research_config.research_type"
        }
        return

    research_depth = research_config.get("research_depth", "balanced")
    llm_model = research_config.get("llm_model", "nova_pro")

    # Get base config and apply depth
    config = get_research_config(research_type)
    config.research_depth = research_depth
    config.llm_model = llm_model

    depth_config = DEPTH_CONFIGS[research_depth]
    config.target_dimensions = depth_config["dimensions"]
    config.target_aspects_per_dimension = depth_config["aspects_per_dimension"]
    config.arxiv_max_results = depth_config["arxiv_max_results"]
    config.web_search_max_results = depth_config["web_search_max_results"]

    # Add optional context
    config_dict = config.to_dict()

    # IMPORTANT: Ensure research_type is preserved in config_dict
    # (from_dict has "basic_web" as default, so we must guarantee it's set correctly)
    if "research_type" not in config_dict or config_dict["research_type"] != research_type:
        logger.warning(f"⚠️  config_dict missing research_type, forcing to: {research_type}")
        config_dict["research_type"] = research_type

    if research_config.get("research_context"):
        config_dict["research_context"] = research_config["research_context"]
    if research_config.get("reference_materials"):
        config_dict["reference_materials"] = research_config["reference_materials"]

    # Log final config for debugging
    logger.info(f"📋 Final research_config: type={config_dict.get('research_type')}, depth={config_dict.get('research_depth')}, model={config_dict.get('llm_model')}")

    # Create context
    context = {
        "user_id": user_id,
    }

    # Execute research workflow
    logger.info(f"[DEBUG] Starting research workflow - session: {session_id}, topic: {topic[:100]}")

    # Now run_research is an async generator, so we can directly iterate
    try:
        async for chunk in agent_instance.run_research(
            topic=topic,
            research_config=config_dict,
            session_id=session_id,
            context=context
        ):
            logger.info(f"[DEBUG] Yielding chunk - session: {session_id}, type: {chunk.get('type', 'unknown')}")
            yield chunk

        logger.info(f"[DEBUG] Research workflow completed - session: {session_id}")

    except Exception as e:
        logger.error(f"[DEBUG] Exception in research workflow - session: {session_id}: {e}")
        raise


if __name__ == "__main__":
    print("="*80)
    print("🔬 Deep Research Agent - AgentCore Runtime")
    print("="*80)

    # Initialize workflow on startup
    try:
        initialize_workflow()
        print("✅ Agent ready for deployment")
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("="*80)
    print("🚀 Starting AgentCore Runtime server...")
    print("="*80)

    # Run the AgentCore app
    app.run()
