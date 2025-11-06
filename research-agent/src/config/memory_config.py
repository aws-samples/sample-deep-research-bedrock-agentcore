"""Memory configuration for AgentCore Memory integration"""
import os
from pathlib import Path


# Memory Configuration
MEMORY_CONFIG = {
    # Memory storage mode: Always use AgentCore for persistent memory
    "memory_storage": "agentcore",

    # AWS Region
    "region": os.getenv("AWS_REGION", "us-west-2"),

    # Memory ID - Single source: AGENTCORE_MEMORY_ID environment variable
    "memory_id": os.getenv("AGENTCORE_MEMORY_ID", "ResearchMemory-2OeNa02agH"),
}


def get_memory_id_from_config() -> str:
    """Get AgentCore Memory ID from environment variable.

    Returns:
        Memory ID string from AGENTCORE_MEMORY_ID env var or default
    """
    return MEMORY_CONFIG.get("memory_id")


def get_memory_storage() -> str:
    """Get memory storage mode: 'ephemeral' or 'agentcore'"""
    return MEMORY_CONFIG.get("memory_storage", "ephemeral")


def get_region() -> str:
    """Get AWS region"""
    return MEMORY_CONFIG.get("region", "us-west-2")


def is_agentcore_enabled() -> bool:
    """Check if AgentCore memory is enabled (always True)"""
    return True


def generate_research_session_id(topic: str) -> str:
    """Generate a unique research session ID based on topic and timestamp.

    Format: research_{timestamp}_{topic_slug}
    Example: research_20251008_143022_ai_systems_protocol

    Args:
        topic: Research topic string

    Returns:
        Session ID string
    """
    import time
    from datetime import datetime

    # Get timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create topic slug (max 40 chars)
    topic_slug = topic.lower()
    topic_slug = ''.join(c if c.isalnum() or c == ' ' else '' for c in topic_slug)
    topic_slug = '_'.join(topic_slug.split())[:40]

    return f"research_{timestamp}_{topic_slug}"
