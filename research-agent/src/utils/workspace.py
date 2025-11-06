"""Workspace Management

Centralized workspace for all file operations during research workflow.

Structure:
workspace/
├── arxiv/          # ArXiv paper downloads
├── dimensions/     # Individual dimension documents
├── final/          # Final merged reports
└── temp/           # Temporary files
    └── {session_id}/  # Session-isolated temporary files
        └── charts/    # Chart images for this session
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class Workspace:
    """Centralized workspace manager"""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize workspace.

        Args:
            base_path: Base workspace path. If None, uses './workspace'
        """
        if base_path is None:
            base_path = os.path.join(os.getcwd(), "workspace")

        self.base_path = Path(base_path)

        # Subdirectories
        self.arxiv_dir = self.base_path / "arxiv"
        self.dimensions_dir = self.base_path / "dimensions"
        self.final_dir = self.base_path / "final"
        self.temp_dir = self.base_path / "temp"

        # Create all directories
        self._create_directories()

    def _create_directories(self):
        """Create all workspace directories"""
        for directory in [
            self.base_path,
            self.arxiv_dir,
            self.dimensions_dir,
            self.final_dir,
            self.temp_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def get_arxiv_path(self, paper_id: str) -> str:
        """
        Get path for ArXiv paper download.

        Args:
            paper_id: ArXiv paper ID

        Returns:
            Full path for paper file
        """
        # Sanitize paper_id for filename
        safe_id = paper_id.replace('/', '_').replace(':', '_')
        return str(self.arxiv_dir / f"{safe_id}.pdf")

    def get_dimension_document_path(self, document_id: str) -> str:
        """
        Get path for dimension document.

        Args:
            document_id: Unique document identifier

        Returns:
            Full path for dimension document
        """
        return str(self.dimensions_dir / f"{document_id}.docx")

    def get_final_report_path(self, topic: str) -> str:
        """
        Get path for final report.

        Args:
            topic: Research topic

        Returns:
            Full path for final report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanitize topic for filename
        safe_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topic)
        safe_topic = safe_topic[:50].strip().replace(' ', '_')

        filename = f"research_report_{safe_topic}_{timestamp}.docx"
        return str(self.final_dir / filename)

    def get_temp_path(self, filename: str) -> str:
        """
        Get path for temporary file.

        Args:
            filename: Temporary filename

        Returns:
            Full path for temp file
        """
        return str(self.temp_dir / filename)

    def get_session_charts_dir(self, session_id: str) -> Path:
        """
        Get session-isolated charts directory.

        Creates directory structure: temp/{session_id}/charts/

        Args:
            session_id: Research session ID for path isolation

        Returns:
            Path object for session's charts directory
        """
        # Sanitize session_id for directory name
        safe_session_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in session_id)

        # Create session-specific charts directory
        session_charts_dir = self.temp_dir / safe_session_id / "charts"
        session_charts_dir.mkdir(parents=True, exist_ok=True)

        return session_charts_dir

    def get_chart_path(self, session_id: str, chart_filename: str) -> str:
        """
        Get path for chart image with session isolation.

        Args:
            session_id: Research session ID for path isolation
            chart_filename: Chart filename (e.g., 'chart_001_structure.png')

        Returns:
            Full path for chart file
        """
        charts_dir = self.get_session_charts_dir(session_id)
        return str(charts_dir / chart_filename)

    def list_dimension_documents(self) -> list[str]:
        """
        List all dimension documents in workspace.

        Returns:
            List of dimension document paths
        """
        return [str(f) for f in self.dimensions_dir.glob("*.docx")]

    def list_arxiv_papers(self) -> list[str]:
        """
        List all downloaded ArXiv papers.

        Returns:
            List of ArXiv paper paths
        """
        return [str(f) for f in self.arxiv_dir.glob("*.pdf")]

    def clean_temp(self):
        """Clean temporary directory"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)

    def clean_session_temp(self, session_id: str):
        """
        Clean temporary files for specific session.

        Args:
            session_id: Research session ID
        """
        import shutil
        safe_session_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in session_id)
        session_dir = self.temp_dir / safe_session_id

        if session_dir.exists():
            shutil.rmtree(session_dir)
            print(f"   🗑️  Cleaned session temp: {session_id}")

    def clean_dimensions(self):
        """Clean dimension documents directory"""
        import shutil
        if self.dimensions_dir.exists():
            shutil.rmtree(self.dimensions_dir)
            self.dimensions_dir.mkdir(parents=True, exist_ok=True)

    def clean_all(self):
        """Clean entire workspace (except final reports)"""
        import shutil

        for directory in [self.arxiv_dir, self.dimensions_dir, self.temp_dir]:
            if directory.exists():
                shutil.rmtree(directory)
                directory.mkdir(parents=True, exist_ok=True)

    def get_info(self) -> dict:
        """
        Get workspace information.

        Returns:
            Dict with workspace stats
        """
        return {
            "base_path": str(self.base_path),
            "arxiv_papers": len(self.list_arxiv_papers()),
            "dimension_documents": len(self.list_dimension_documents()),
            "final_reports": len(list(self.final_dir.glob("*.docx"))),
        }


# Global workspace instance
_workspace: Optional[Workspace] = None


def get_workspace(base_path: Optional[str] = None) -> Workspace:
    """
    Get or create global workspace instance.

    Args:
        base_path: Optional base path override

    Returns:
        Workspace instance
    """
    global _workspace

    if _workspace is None or base_path is not None:
        _workspace = Workspace(base_path)

    return _workspace


def reset_workspace():
    """Reset workspace (for testing)"""
    global _workspace
    _workspace = None
