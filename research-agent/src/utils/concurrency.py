"""Concurrency control utilities for workflow nodes

This module provides semaphore-based concurrency limiting for parallel node executions.
Each node type can have its own concurrency limit to prevent overwhelming the system
with too many parallel API calls or resource-intensive operations.

Usage:
    async with limit_concurrency("research", "AI Ethics"):
        # Your node logic here
        result = await perform_research()
"""

import asyncio
from typing import Dict, Optional
from contextlib import asynccontextmanager

from src.config.research_config import CONCURRENCY_LIMITS


# Global semaphore registry
# Key: node type (e.g., "research", "dimension_reduction")
# Value: asyncio.Semaphore instance
_semaphores: Dict[str, asyncio.Semaphore] = {}
_lock = asyncio.Lock()


async def get_node_semaphore(node_type: str) -> Optional[asyncio.Semaphore]:
    """
    Get or create a semaphore for a specific node type.

    Args:
        node_type: Type of node (e.g., "research", "dimension_reduction")

    Returns:
        asyncio.Semaphore if limit is set, None if unlimited

    Example:
        >>> semaphore = await get_node_semaphore("research")
        >>> async with semaphore:
        ...     await do_research()
    """
    # Check if this node type has a limit
    limit = CONCURRENCY_LIMITS.get(node_type)

    if limit is None:
        # No limit specified - unlimited concurrency
        return None

    # Create semaphore if it doesn't exist
    async with _lock:
        if node_type not in _semaphores:
            _semaphores[node_type] = asyncio.Semaphore(limit)
            print(f"🔒 Created semaphore for '{node_type}' with limit={limit}")

    return _semaphores[node_type]


@asynccontextmanager
async def limit_concurrency(node_type: str, node_name: str = ""):
    """
    Async context manager to limit concurrency for a node execution.

    Automatically acquires and releases the semaphore for the node type.
    If no limit is set, executes without restriction.

    Args:
        node_type: Type of node (e.g., "research", "dimension_reduction")
        node_name: Optional name for logging (e.g., aspect name)

    Yields:
        None

    Example:
        >>> async with limit_concurrency("research", "AI Ethics"):
        ...     result = await perform_research()
    """
    semaphore = await get_node_semaphore(node_type)

    if semaphore is None:
        # No limit - proceed immediately
        yield
        return

    # Wait for semaphore
    if node_name:
        print(f"⏳ [{node_type}] Waiting for slot: {node_name}")
    else:
        print(f"⏳ [{node_type}] Waiting for execution slot")

    async with semaphore:
        if node_name:
            print(f"▶️  [{node_type}] Starting: {node_name}")
        else:
            print(f"▶️  [{node_type}] Starting execution")

        try:
            yield
        finally:
            if node_name:
                print(f"✅ [{node_type}] Completed: {node_name}")
            else:
                print(f"✅ [{node_type}] Completed execution")


def reset_semaphores():
    """
    Reset all semaphores (useful for testing or configuration changes).

    Warning: Should not be called while nodes are running.
    """
    global _semaphores
    _semaphores.clear()
    print("🔄 All semaphores reset")


def get_current_limits() -> Dict[str, Optional[int]]:
    """
    Get current concurrency limits for all node types.

    Returns:
        Dictionary mapping node types to their limits (None = unlimited)

    Example:
        >>> limits = get_current_limits()
        >>> print(limits)
        {'research': 3, 'dimension_reduction': 1, 'aspect_analysis': None}
    """
    return CONCURRENCY_LIMITS.copy()


def update_limit(node_type: str, limit: Optional[int]):
    """
    Dynamically update concurrency limit for a node type.

    Args:
        node_type: Type of node to update
        limit: New limit (None for unlimited, int for specific limit)

    Note:
        This creates a new semaphore. Existing operations will continue
        with the old limit until they complete.

    Example:
        >>> update_limit("research", 5)  # Allow 5 concurrent research tasks
        >>> update_limit("research", None)  # Remove limit
    """
    CONCURRENCY_LIMITS[node_type] = limit

    # Reset semaphore for this node type so it gets recreated with new limit
    if node_type in _semaphores:
        del _semaphores[node_type]

    print(f"🔧 Updated '{node_type}' concurrency limit to {limit}")
