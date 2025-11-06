"""Stage 5: Document Merge Node

This node merges dimension documents into a single final report.
Uses pure Python - NO LLM calls, making it fast and deterministic.
"""

import time
from datetime import datetime
from typing import Dict, Any
from langsmith import traceable

from src.state import ResearchState
from src.utils.document_merger import (
    merge_dimension_documents,
    collect_references_from_documents,
    add_references_section
)
from docx import Document


@traceable(name="document_merge_node")
def document_merge_node(state: ResearchState) -> Dict[str, Any]:
    """
    Merge dimension documents into final report.

    Pure Python implementation - no LLM calls.

    Args:
        state: Full research state with dimension_documents

    Returns:
        Dict with report_file path
    """
    print(f"\n{'='*80}")
    print(f"STAGE 5: MERGING DOCUMENTS")
    print(f"{'='*80}")

    start_time = time.time()

    topic = state.get("topic", "Research Report")
    dimensions = state.get("dimensions", [])
    dimension_documents = state.get("dimension_documents", {})

    print(f"\nMerging {len(dimension_documents)} dimension documents...")

    # Collect dimension document paths in order
    dimension_doc_paths = []
    for dimension in dimensions:
        doc_path = dimension_documents.get(dimension)
        if doc_path and not doc_path.startswith("error_"):
            dimension_doc_paths.append(doc_path)
            print(f"   ✓ {dimension}: {doc_path}")
        else:
            print(f"   ✗ {dimension}: Missing or error")

    if not dimension_doc_paths:
        print(f"\n❌ No valid dimension documents to merge")
        return {
            "report_file": None,
            "current_stage": "merge_failed"
        }

    # Generate output filename using workspace
    from src.utils.workspace import get_workspace

    workspace = get_workspace()
    output_filename = workspace.get_final_report_path(topic)

    # Merge documents
    print(f"\n📄 Creating final report...")

    try:
        # Use simple merge
        final_path = merge_dimension_documents(
            dimension_doc_paths=dimension_doc_paths,
            output_path=output_filename,
            title=f"Research Report: {topic[:100]}"
        )

        # Collect and add references
        print(f"   Collecting references...")
        references = collect_references_from_documents(dimension_doc_paths)

        if references:
            # Load the merged document and add references
            doc = Document(final_path)
            add_references_section(doc, references)
            doc.save(final_path)
            print(f"   ✓ Added {len(references)} unique references")

        elapsed = time.time() - start_time

        print(f"\n✅ Final report created in {elapsed:.2f}s")
        print(f"   File: {output_filename}")
        print(f"   Dimensions: {len(dimension_doc_paths)}")
        if references:
            print(f"   References: {len(references)}")

        return {
            "report_file": output_filename,
            "current_stage": "merge_complete"
        }

    except Exception as e:
        print(f"\n❌ Merge failed: {e}")
        import traceback
        traceback.print_exc()

        return {
            "report_file": None,
            "current_stage": "merge_failed"
        }
