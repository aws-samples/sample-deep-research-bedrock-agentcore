"""AgentCore Memory Saver for research agent checkpointing."""

from typing import List, Dict, Any, Optional
from langgraph_checkpoint_aws import AgentCoreMemorySaver
import boto3
from botocore.config import Config


class ResearchMemorySaver(AgentCoreMemorySaver):
    """AgentCoreMemorySaver for research agents.

    Stores conversation history and agent state in AWS Bedrock AgentCore Memory.
    Checkpoints are stored by thread_id for session continuity.

    Provides additional utility methods for inspecting and managing research sessions.
    """

    def __init__(self, memory_id: str, region_name: str = 'us-west-2'):
        """Initialize ResearchMemorySaver with timeout configuration.

        Args:
            memory_id: AgentCore Memory ID
            region_name: AWS region (default: us-west-2)
        """
        # AgentCoreMemorySaver already sets default timeout:
        # boto3_kwargs.setdefault("config", Config(read_timeout=600))
        #
        # We don't need to override it - 600 seconds (10 minutes) is sufficient
        # for checkpoint operations.
        #
        # Issue: Passing config= explicitly causes TypeError due to duplicate
        # 'config' parameter in boto3.client() call inside AgentCoreEventClient.
        # Solution: Use default timeout configuration from parent class.

        super().__init__(
            memory_id=memory_id,
            region_name=region_name
            # Don't pass config - let parent use default read_timeout=600
        )

    def put(self, config, checkpoint, metadata, new_versions):
        """Override put() to add logging around checkpoint saves.

        This helps diagnose if checkpoint save operations are causing hangs.

        Args:
            config: Checkpoint configuration
            checkpoint: Checkpoint data
            metadata: Checkpoint metadata
            new_versions: Version information for checkpoint
        """
        import logging
        import time

        logger = logging.getLogger(__name__)
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")

        logger.info(f"🔵 [CHECKPOINT] Starting checkpoint save for thread: {thread_id[:50]}...")
        start_time = time.time()

        try:
            result = super().put(config, checkpoint, metadata, new_versions)
            elapsed = time.time() - start_time
            logger.info(f"✅ [CHECKPOINT] Saved successfully in {elapsed:.2f}s for thread: {thread_id[:50]}...")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [CHECKPOINT] Save failed after {elapsed:.2f}s for thread: {thread_id[:50]}...: {e}", exc_info=True)
            raise

    def get(self, config):
        """Override get() to add logging around checkpoint loads.

        This helps diagnose if checkpoint load operations are causing hangs.
        """
        import logging
        import time

        logger = logging.getLogger(__name__)
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")

        logger.info(f"🔵 [CHECKPOINT] Starting checkpoint load for thread: {thread_id[:50]}...")
        start_time = time.time()

        try:
            result = super().get(config)
            elapsed = time.time() - start_time
            logger.info(f"✅ [CHECKPOINT] Loaded successfully in {elapsed:.2f}s for thread: {thread_id[:50]}...")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [CHECKPOINT] Load failed after {elapsed:.2f}s for thread: {thread_id[:50]}...: {e}", exc_info=True)
            raise

    def get_session_thread_ids(self, session_id: str) -> List[str]:
        """Get all thread IDs associated with a research session.

        Args:
            session_id: Research session ID

        Returns:
            List of thread IDs for this session with aspect names
        """
        import hashlib
        from src.utils.session_logger import get_session_logger

        session_logger = get_session_logger()
        logs = session_logger.get_session_logs(session_id)

        thread_ids = []

        for log in logs:
            if log.get("status") == "completed":
                results = log.get("results", {})
                aspects_by_dimension = results.get("aspects_by_dimension", {})

                for dimension, aspects in aspects_by_dimension.items():
                    for aspect in aspects:
                        # Reconstruct thread_id using hash (same logic as research_agent.py)
                        aspect_name = aspect if isinstance(aspect, str) else aspect.get("name", "unknown")

                        # Create aspect identifier and hash
                        aspect_identifier = f"{dimension}::{aspect_name}"
                        aspect_hash = hashlib.sha256(aspect_identifier.encode()).hexdigest()[:16]

                        # Thread ID: {session_id}_{hash}
                        thread_id = f"{session_id}_{aspect_hash}"
                        thread_ids.append((thread_id, aspect_name, dimension))

        return thread_ids

    def get_session_checkpoints(self, session_id: str) -> Dict[str, List[Any]]:
        """Get all checkpoints for a research session grouped by thread_id.

        Args:
            session_id: Research session ID

        Returns:
            Dict mapping thread_id to list of checkpoints
        """
        thread_infos = self.get_session_thread_ids(session_id)

        checkpoints_by_thread = {}

        for thread_info in thread_infos:
            # Unpack tuple: (thread_id, aspect_name, dimension)
            thread_id, aspect_name, dimension = thread_info

            try:
                # List checkpoints for this thread
                thread_checkpoints = []
                config = {"configurable": {"thread_id": thread_id, "actor_id": "default_user"}}

                # Get checkpoint history for this thread
                for checkpoint in self.list(config):
                    thread_checkpoints.append(checkpoint)

                if thread_checkpoints:
                    checkpoints_by_thread[thread_id] = thread_checkpoints

            except Exception as e:
                print(f"⚠️  Could not retrieve checkpoints for {thread_id}: {e}")

        return checkpoints_by_thread

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of a research session including logs and checkpoint stats.

        Args:
            session_id: Research session ID

        Returns:
            Dict with session metadata, logs, and checkpoint statistics
        """
        from src.utils.session_logger import get_session_logger

        session_logger = get_session_logger()
        logs = session_logger.get_session_logs(session_id)
        thread_infos = self.get_session_thread_ids(session_id)

        # Get checkpoint statistics
        checkpoint_stats = {}
        total_checkpoints = 0

        for thread_info in thread_infos:
            thread_id, aspect_name, dimension = thread_info
            try:
                config = {"configurable": {"thread_id": thread_id, "actor_id": "default_user"}}
                checkpoint_count = len(list(self.list(config)))
                checkpoint_stats[thread_id] = checkpoint_count
                total_checkpoints += checkpoint_count
            except Exception:
                checkpoint_stats[thread_id] = 0

        return {
            "session_id": session_id,
            "logs": logs,
            "thread_ids": thread_infos,
            "thread_count": len(thread_infos),
            "checkpoint_stats": checkpoint_stats,
            "total_checkpoints": total_checkpoints
        }

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """List all research sessions from session logs.

        Returns:
            List of session summaries
        """
        from src.utils.session_logger import get_session_logger

        session_logger = get_session_logger()
        logs = session_logger.get_session_logs()

        if not logs:
            return []

        # Group by session_id
        sessions = {}
        for log in logs:
            session_id = log.get("session_id")
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(log)

        # Build session summaries
        session_list = []
        for session_id, session_logs in sorted(sessions.items()):
            start_log = next((log for log in session_logs if log.get("status") == "started"), None)
            complete_log = next((log for log in session_logs if log.get("status") == "completed"), None)

            summary = {
                "session_id": session_id,
                "topic": start_log.get("topic", "N/A") if start_log else "N/A",
                "started": start_log.get("timestamp", "N/A") if start_log else "N/A",
                "status": "completed" if complete_log else "in_progress",
            }

            if complete_log:
                results = complete_log.get("results", {})
                summary.update({
                    "dimension_count": results.get("dimension_count", 0),
                    "total_aspects": results.get("total_aspects", 0),
                    "elapsed_time_seconds": results.get("elapsed_time_seconds", 0)
                })

            session_list.append(summary)

        return session_list
