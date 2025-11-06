"""Document Conversion Node

Converts the final markdown document (with embedded charts) to Word and PDF formats.

This node runs AFTER chart_generation_node has inserted all charts into the markdown.
It simply converts the markdown to distributable formats.
"""

import time
import logging
from typing import Dict, Any
from pathlib import Path

from src.state import ResearchState
from src.nodes.report_writing import markdown_to_docx, docx_to_pdf
from src.utils.workspace import get_workspace

logger = logging.getLogger(__name__)


def document_conversion_node(state: ResearchState) -> Dict[str, Any]:
    """
    Convert markdown report with charts to Word and PDF.

    This node:
    1. Reads the markdown file (with embedded chart references)
    2. Converts to Word document (images are embedded during conversion)
    3. Converts Word to PDF

    Args:
        state: ResearchState with:
            - draft_report_file: Path to markdown file with charts
            - topic: Research topic for filename

    Returns:
        Dict with report_file (Word) and report_pdf_file (PDF) paths
    """
    logger.info("DOCUMENT CONVERSION (Markdown → Word → PDF)")

    start_time = time.time()

    try:
        # Get required state
        draft_report_file = state.get("draft_report_file")
        topic = state.get("topic", "research")

        if not draft_report_file or not Path(draft_report_file).exists():
            logger.warning("No draft report file found")
            return {"report_file": None, "report_pdf_file": None}

        workspace = get_workspace()

        # Read markdown content
        with open(draft_report_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Check if charts are embedded
        chart_count = markdown_content.count('![Chart]')
        figure_count = markdown_content.count('*Figure ')

        # Prepare output paths
        import time as time_module
        timestamp = time_module.strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topic)
        safe_topic = safe_topic[:50].strip().replace(' ', '_')

        final_docx_path = str(workspace.final_dir / f"research_report_{safe_topic}_{timestamp}.docx")
        final_pdf_path = str(workspace.final_dir / f"research_report_{safe_topic}_{timestamp}.pdf")

        # Step 1: Convert to Word
        markdown_to_docx(markdown_content, final_docx_path)

        # Step 2: Convert to PDF
        try:
            docx_to_pdf(final_docx_path, final_pdf_path)
        except Exception as e:
            logger.warning(f"PDF conversion failed: {e}")
            final_pdf_path = None

        elapsed = time.time() - start_time
        logger.info(f"Document conversion completed in {elapsed:.2f}s - Word: {final_docx_path}, PDF: {final_pdf_path or 'N/A'}")

        return {
            "report_file": final_docx_path,
            "report_pdf_file": final_pdf_path
        }

    except Exception as e:
        logger.error(f"Document conversion failed: {e}", exc_info=True)
        return {"report_file": None, "report_pdf_file": None}
