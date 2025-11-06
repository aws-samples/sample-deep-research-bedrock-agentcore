"""Editor tools for report refinement

Tools that work directly on the draft markdown file via RunnableConfig.
The file path is provided through config.configurable, not as tool parameters.
All changes are immediately persisted to the file.

Thread-safe with file locking to prevent race conditions when multiple tools
execute in parallel.
"""

from langchain.tools import tool
import os
import threading
from langchain_core.runnables import RunnableConfig
from typing import Annotated

# Global file lock for thread-safe file operations
_file_locks = {}
_locks_lock = threading.Lock()


def get_draft_path(config: RunnableConfig) -> str:
    """Get the draft report file path from RunnableConfig.

    Args:
        config: RunnableConfig containing draft_report_file in configurable

    Returns:
        Path to the draft markdown file

    Raises:
        ValueError: If draft_report_file not found or file doesn't exist
    """
    draft_path = config.get("configurable", {}).get("draft_report_file")
    if not draft_path:
        raise ValueError(
            "No draft_report_file found in config. "
            "Make sure the agent is invoked with draft_report_file in config.configurable."
        )
    if not os.path.exists(draft_path):
        raise ValueError(f"Draft file does not exist: {draft_path}")
    return draft_path


def get_file_lock(file_path: str) -> threading.Lock:
    """Get or create a lock for a specific file path.

    Thread-safe lock acquisition to prevent race conditions when multiple
    tools try to edit the same file simultaneously.

    Args:
        file_path: Path to the file to lock

    Returns:
        Threading lock for the file
    """
    with _locks_lock:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]


@tool
def replace_text(
    find_text_param: str,
    replace_with: str,
    config: Annotated[RunnableConfig, "Injected configuration"],
    max_replacements: int = -1
) -> str:
    """Replace text in the document and save changes immediately.

    The document file path is automatically obtained from config (draft_report_file).
    Use this tool to fix awkward transitions, improve flow, or correct text.

    Thread-safe: Uses file locking to prevent race conditions when multiple
    replace_text calls execute in parallel.

    Args:
        find_text_param: Text to find and replace
        replace_with: Text to replace with
        max_replacements: Maximum number of replacements (-1 for all, default: -1)

    Returns:
        JSON string with operation result
    """
    import json

    # Get file path and lock
    draft_path = get_draft_path(config)
    file_lock = get_file_lock(draft_path)

    # Acquire lock for thread-safe file operations
    with file_lock:
        # Read from draft file
        with open(draft_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if max_replacements == -1:
            new_content = content.replace(find_text_param, replace_with)
            count = content.count(find_text_param)
        else:
            parts = content.split(find_text_param, max_replacements)
            new_content = replace_with.join(parts)
            count = min(content.count(find_text_param), max_replacements)

        # Write back to draft file immediately
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    return json.dumps({
        "status": "success",
        "replacements_made": count
    }, indent=2)


@tool
def write_summary_and_conclusion(
    summary_content: str,
    conclusion_content: str,
    config: Annotated[RunnableConfig, "Injected configuration"]
) -> str:
    """Write both Executive Summary and Conclusion sections in one operation.

    The document file path is automatically obtained from config (draft_report_file).
    This tool replaces both placeholders with your content in a single operation.

    Thread-safe: Uses file locking to prevent race conditions.

    Args:
        summary_content: Executive Summary content (200-300 words)
        conclusion_content: Conclusion content (300-400 words)

    Returns:
        JSON string with operation result
    """
    import json

    # Get file path and lock
    draft_path = get_draft_path(config)
    file_lock = get_file_lock(draft_path)

    print(f"\n[write_summary_and_conclusion] Working on file: {draft_path}")

    # Acquire lock for thread-safe file operations
    with file_lock:
        # Read from draft file
        with open(draft_path, 'r', encoding='utf-8') as f:
            document_content = f.read()

        # Replace both placeholders
        summary_placeholder = "[EXECUTIVE_SUMMARY_TO_BE_GENERATED]"
        conclusion_placeholder = "[CONCLUSION_TO_BE_GENERATED]"

        # Check if placeholders exist
        missing = []
        if summary_placeholder not in document_content:
            missing.append("Executive Summary")
        if conclusion_placeholder not in document_content:
            missing.append("Conclusion")

        if missing:
            print(f"[write_summary_and_conclusion] ERROR: Placeholders not found: {missing}")
            return json.dumps({
                "status": "error",
                "message": f"Placeholders not found: {', '.join(missing)}. Sections may already be written."
            }, indent=2)

        print(f"[write_summary_and_conclusion] Replacing both placeholders...")
        # Replace both placeholders
        new_content = document_content.replace(summary_placeholder, summary_content)
        new_content = new_content.replace(conclusion_placeholder, conclusion_content)

        # Write back to draft file
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"[write_summary_and_conclusion] File saved successfully")

    summary_words = len(summary_content.split())
    conclusion_words = len(conclusion_content.split())

    return json.dumps({
        "status": "success",
        "summary_word_count": summary_words,
        "conclusion_word_count": conclusion_words,
        "total_word_count": summary_words + conclusion_words
    }, indent=2)
