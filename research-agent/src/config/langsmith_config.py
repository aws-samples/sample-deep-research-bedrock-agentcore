"""LangSmith configuration for tracing and monitoring"""

import os
import uuid
from typing import Dict, Any, Optional


def is_langsmith_enabled() -> bool:
    """
    Check if LangSmith tracing is enabled.

    Returns:
        True if LANGCHAIN_TRACING_V2 is set to true
    """
    return os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"


def get_langsmith_project() -> str:
    """
    Get LangSmith project name.

    Returns:
        Project name from environment or default
    """
    return os.getenv("LANGCHAIN_PROJECT", "dimensional-research-agent")


def create_run_config(
    run_name: str,
    tags: Optional[list] = None,
    metadata: Optional[dict] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create LangSmith run configuration for workflow execution.

    Args:
        run_name: Name of the run (e.g., "topic_analysis_run")
        tags: List of tags for categorization (e.g., ["research", "stage1"])
        metadata: Additional metadata dictionary
        session_id: Optional session ID for tracking

    Returns:
        Configuration dictionary for workflow.invoke()
    """
    # Generate session ID if not provided
    if not session_id:
        session_id = f"research-session-{uuid.uuid4()}"

    # Default tags
    default_tags = ["dimensional-research"]
    if tags:
        default_tags.extend(tags)

    # Build config
    config = {
        "configurable": {"thread_id": session_id},
        "run_name": run_name,
        "run_id": uuid.uuid4(),
        "tags": default_tags,
    }

    # Add metadata if provided
    if metadata:
        config["metadata"] = metadata

    return config


def create_stage_config(stage_name: str, topic: str) -> Dict[str, Any]:
    """
    Create configuration for a specific research stage.

    Args:
        stage_name: Name of the stage (topic_analysis, aspect_analysis, research)
        topic: Research topic

    Returns:
        Configuration dictionary
    """
    # Stage-specific tags
    stage_tags = {
        "topic_analysis": ["stage1", "sequential", "dimensions"],
        "aspect_analysis": ["stage2", "parallel", "aspects"],
        "research": ["stage3", "parallel", "react-agent", "arxiv"],
    }

    tags = stage_tags.get(stage_name, [])

    metadata = {
        "stage": stage_name,
        "topic": topic[:100],  # Truncate long topics
        "environment": "dev"
    }

    return create_run_config(
        run_name=f"{stage_name}_run",
        tags=tags,
        metadata=metadata
    )


def print_langsmith_info():
    """Print LangSmith configuration information"""
    if is_langsmith_enabled():
        project = get_langsmith_project()
        print("📊 LangSmith Tracing: ENABLED")
        print(f"   Project: {project}")
        print(f"   View traces at: https://smith.langchain.com/")
    else:
        print("📊 LangSmith Tracing: DISABLED")
        print("   Set LANGCHAIN_TRACING_V2=true to enable")
