"""Session logging utilities for research workflow"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class SessionLogger:
    """Logs research session metadata for tracking and auditing"""

    def __init__(self, log_dir: Optional[str] = None):
        """Initialize session logger

        Args:
            log_dir: Directory to store session logs (default: workspace/logs)
        """
        if log_dir is None:
            from src.utils.workspace import get_workspace
            workspace = get_workspace()
            log_dir = workspace.base_path / "logs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Session log file
        self.sessions_file = self.log_dir / "research_sessions.jsonl"

    def log_session_start(
        self,
        session_id: str,
        topic: str,
        research_config: Dict[str, Any],
        research_context: Optional[str] = None
    ) -> None:
        """Log research session start with metadata

        Args:
            session_id: Unique research session ID
            topic: Research topic
            research_config: Research configuration dict
            research_context: Optional user-provided context
        """
        log_entry = {
            "session_id": session_id,
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "started",
            "config": {
                "target_dimensions": research_config.get("target_dimensions", 3),
                "target_aspects_per_dimension": research_config.get("target_aspects_per_dimension", 3),
                "research_depth": research_config.get("research_depth", "standard"),
                "research_type": research_config.get("research_type", "comprehensive"),
                "tools_enabled": research_config.get("tools", []),
                "has_references": bool(research_config.get("reference_materials", [])),
                "reference_count": len(research_config.get("reference_materials", []))
            },
            "research_context": research_context if research_context else None
        }

        # Append to JSONL file
        with open(self.sessions_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        print(f"📝 Session logged: {self.sessions_file}")

    def log_session_complete(
        self,
        session_id: str,
        dimensions: list,
        aspects_by_dimension: Dict[str, list],
        report_file: str,
        elapsed_time: float,
        s3_uploads: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log research session completion

        Args:
            session_id: Research session ID
            dimensions: List of dimensions
            aspects_by_dimension: Aspects grouped by dimension
            report_file: Final report file path
            elapsed_time: Total workflow time in seconds
            s3_uploads: Optional S3 upload metadata
        """
        log_entry = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "results": {
                "dimensions": dimensions,
                "dimension_count": len(dimensions),
                "total_aspects": sum(len(aspects) for aspects in aspects_by_dimension.values()),
                "aspects_by_dimension": {
                    dim: [asp.get("name", str(asp)) if isinstance(asp, dict) else str(asp)
                          for asp in aspects]
                    for dim, aspects in aspects_by_dimension.items()
                },
                "report_file": report_file,
                "elapsed_time_seconds": elapsed_time
            }
        }

        # Append to JSONL file
        with open(self.sessions_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        print(f"📝 Session completion logged: {self.sessions_file}")

    def get_session_logs(self, session_id: Optional[str] = None) -> list:
        """Retrieve session logs

        Args:
            session_id: Optional session ID to filter logs

        Returns:
            List of log entries
        """
        if not self.sessions_file.exists():
            return []

        logs = []
        with open(self.sessions_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    log = json.loads(line)
                    if session_id is None or log.get("session_id") == session_id:
                        logs.append(log)

        return logs


# Global session logger instance
_session_logger = None


def get_session_logger() -> SessionLogger:
    """Get or create global session logger instance"""
    global _session_logger
    if _session_logger is None:
        _session_logger = SessionLogger()
    return _session_logger
