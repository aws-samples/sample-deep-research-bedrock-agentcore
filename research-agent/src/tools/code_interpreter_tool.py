"""Code Interpreter-based chart generation tools

Three tools for chart generation workflow:
1. read_document_lines: Read specific line range from draft document
2. generate_and_validate_chart: Generate chart from Python code → returns image preview
3. bring_and_insert_chart: Insert generated chart into document → returns success/failure
"""

from langchain.tools import tool
from typing import Annotated, Dict, Any, Tuple
from langchain_core.runnables import RunnableConfig
import json
import os
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# Session-based temporary chart storage
_chart_storage = {}  # session_id -> {filename -> chart_data}


@tool
def read_document_lines(
    start_line: int,
    end_line: int,
    config: Annotated[RunnableConfig, "Injected configuration"] = None
) -> str:
    """Read a section of the research document by line range.

    Read document sequentially in 50-line chunks to find visualization opportunities.

    Args:
        start_line: Starting line (1-indexed, inclusive)
        end_line: Ending line (1-indexed, inclusive). Max 50 lines per read recommended.

    Returns:
        Document content with line numbers. Look for numeric data, processes, or concepts to visualize.
    """
    if not config:
        return "❌ Error: No configuration provided"

    draft_path = config.get("configurable", {}).get("draft_report_file")
    if not draft_path:
        return "❌ Error: No draft_report_file in config"

    try:
        with open(draft_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Validate line numbers
        if start_line < 1:
            start_line = 1
        if end_line > total_lines:
            end_line = total_lines
        if start_line > end_line:
            return f"❌ Error: start_line ({start_line}) > end_line ({end_line})"

        # Convert to 0-indexed and extract
        start_idx = start_line - 1
        end_idx = end_line

        selected_lines = lines[start_idx:end_idx]

        # Format with line numbers
        formatted_content = []
        for i, line in enumerate(selected_lines, start=start_line):
            formatted_content.append(f"{i:4d} | {line.rstrip()}")

        result = "\n".join(formatted_content)

        return f"""📄 Document lines {start_line}-{end_line} (of {total_lines} total):

{result}

Use this content to identify numeric data for chart generation."""

    except FileNotFoundError:
        return f"❌ Error: Document file not found: {draft_path}"
    except Exception as e:
        return f"❌ Error reading document: {str(e)}"


@tool
def generate_and_validate_chart(
    python_code: str,
    chart_filename: str = None,
    config: Annotated[RunnableConfig, "Injected configuration"] = None
) -> list:
    """Generate chart and return with image for model to review visually.

    Args:
        python_code: Complete Python code for chart generation.
                    Available: matplotlib.pyplot, seaborn, pandas, numpy
                    Required: plt.savefig('filename.png', dpi=300, bbox_inches='tight')
        chart_filename: PNG filename (required for charts). Must exactly match filename in savefig().
                       Example: "performance_chart.png"

    Returns:
        List with text and image content blocks for multimodal model review.
    """
    from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
    from src.utils.workspace import get_workspace

    # Get configuration
    session_id = config.get("configurable", {}).get("research_session_id", "default_session") if config else "default_session"

    # Validate chart_filename if provided
    if chart_filename is not None and not chart_filename.endswith('.png'):
        return f"""❌ Invalid filename

**Error:** chart_filename must end with .png

You provided: {chart_filename}
Please use a .png filename (e.g., "my_chart.png")
"""

    try:
        logger.info(f"Generating chart via Code Interpreter: {chart_filename}")

        # 1. Execute Python code in Bedrock Code Interpreter
        region = os.getenv('AWS_REGION', 'us-west-2')
        code_interpreter = CodeInterpreter(region)
        code_interpreter.start()

        logger.info(f"[DEBUG] Code Interpreter executeCode starting - session: {session_id}")
        response = code_interpreter.invoke("executeCode", {
            "code": python_code,
            "language": "python",
            "clearContext": False
        })
        logger.info(f"[DEBUG] Code Interpreter executeCode returned - session: {session_id}")

        # Check for errors
        execution_success = False
        execution_output = ""
        for event in response.get("stream", []):
            result = event.get("result", {})
            if result.get("isError", False):
                error_msg = result.get("structuredContent", {}).get("stderr", "Unknown error")
                logger.error(f"Code Interpreter execution failed: {error_msg[:200]}")
                code_interpreter.stop()

                return f"""❌ Python code execution failed

**Error Output:**
```
{error_msg}
```

**Your Code:**
```python
{python_code[:500]}{'...' if len(python_code) > 500 else ''}
```

Please fix the error and try again.
"""

            execution_output = result.get("structuredContent", {}).get("stdout", "")
            execution_success = True

        if not execution_success:
            logger.warning("Code Interpreter: No result returned")
            code_interpreter.stop()
            return f"""❌ No result from Bedrock Code Interpreter

The code was sent but no result was returned.
Please try again or simplify your code.
"""

        logger.info("Code Interpreter execution successful")

        # 2. List all files created during execution (always show)
        available_files = []
        try:
            file_list_response = code_interpreter.invoke("listFiles", {"path": ""})
            for event in file_list_response.get("stream", []):
                result = event.get("result", {})

                # Parse file list from content
                if "content" in result:
                    for item in result.get("content", []):
                        # Only include actual files, not directories
                        if item.get("description") == "File":
                            filename = item.get("name", "")
                            if filename:
                                available_files.append(filename)
        except Exception as list_err:
            print(f"Warning: Could not list files: {list_err}")
            import traceback
            traceback.print_exc()

        # 3. Download file if chart_filename is provided
        file_content = None
        if chart_filename is not None:
            try:
                # Download file using readFiles action
                download_response = code_interpreter.invoke("readFiles", {"paths": [chart_filename]})

                for event in download_response.get("stream", []):
                    result = event.get("result", {})
                    if "content" in result and len(result["content"]) > 0:
                        content_block = result["content"][0]
                        # File content can be in 'data' (bytes) or 'resource.blob'
                        if "data" in content_block:
                            file_content = content_block["data"]
                        elif "resource" in content_block and "blob" in content_block["resource"]:
                            file_content = content_block["resource"]["blob"]

                        if file_content:
                            break

                if file_content is None:
                    raise Exception(f"No file content returned for {chart_filename}")

                logger.info(f"Successfully downloaded chart file: {chart_filename} ({len(file_content)} bytes)")
            except Exception as e:
                logger.error(f"Failed to download chart file {chart_filename}: {str(e)}")
                code_interpreter.stop()
                return f"""❌ Failed to download file

**Error:** Could not download '{chart_filename}'
**Exception:** {str(e)}

**Available files in session:** {', '.join(available_files) if available_files else 'None'}

**Fix:** Make sure your code creates the file with the exact filename:
```python
plt.savefig('{chart_filename}', dpi=300, bbox_inches='tight')
```
"""

        code_interpreter.stop()

        # 4. Return results based on whether file was requested
        if chart_filename is not None and file_content is not None:
            # File was requested and downloaded - save to workspace
            workspace = get_workspace()
            chart_path = workspace.get_chart_path(session_id, chart_filename)

            # Ensure directory exists
            os.makedirs(os.path.dirname(chart_path), exist_ok=True)

            # Write file content
            with open(chart_path, 'wb') as f:
                f.write(file_content)

            # Store chart metadata in session storage (keyed by filename)
            if session_id not in _chart_storage:
                _chart_storage[session_id] = {}

            _chart_storage[session_id][chart_filename] = {
                'filename': chart_filename,
                'file_path': chart_path,
                'original_code': python_code,
                'execution_output': execution_output
            }

            # Get file size for confirmation
            file_size_kb = len(file_content) / 1024
            image_b64 = base64.b64encode(file_content).decode('utf-8')

            # Return as list with text and image for multimodal review
            # Model can see the chart and verify it looks correct
            return [
                {
                    "type": "text",
                    "text": f"✅ Chart generated: {chart_filename} ({file_size_kb:.1f} KB)\n\nReview the chart below. If it looks good, proceed with bring_and_insert_chart."
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64
                    }
                }
            ]
        else:
            # No file requested - just return execution output
            return f"""✅ Code executed successfully!

**Execution Output:**
```
{execution_output if execution_output else 'Code executed with no output'}
```

**Available Files:** {', '.join(available_files) if available_files else 'None'}

If you created a file and want to download it, call this tool again with the `chart_filename` parameter.
"""

    except Exception as e:
        import traceback
        return f"""❌ Failed to execute code

**Error:** {str(e)}

**Traceback:**
```
{traceback.format_exc()}
```
"""


@tool
def bring_and_insert_chart(
    chart_filename: str,
    chart_title: str,
    chart_description: str,
    insertion_location: str,
    config: Annotated[RunnableConfig, "Injected configuration"]
) -> str:
    """Insert previously generated chart into markdown document with auto-numbered caption.

    Args:
        chart_filename: Exact filename from generate_and_validate_chart (e.g., "perf_chart.png")
        chart_title: Title for chart caption
        chart_description: 1-2 sentence description of what chart shows
        insertion_location: Line number where to insert chart (e.g., "line:125" to insert after line 125)

    Returns:
        Success with figure number or error.
    """
    from src.utils.workspace import get_workspace
    import re

    # Get configuration
    session_id = config.get("configurable", {}).get("research_session_id", "default_session")
    draft_path = config.get("configurable", {}).get("draft_report_file")

    logger.info(f"Inserting chart into document: {chart_filename} at {insertion_location}")

    if not draft_path:
        return "❌ Error: No draft_report_file in config"

    # 1. Retrieve chart from storage
    if session_id not in _chart_storage or chart_filename not in _chart_storage[session_id]:
        logger.error(f"Chart file not found in storage: {chart_filename}")
        available_files = list(_chart_storage.get(session_id, {}).keys())
        return f"""❌ Chart file not found

**Error:** Chart filename '{chart_filename}' not found in session storage.

**Available chart files:** {', '.join(available_files) if available_files else 'None'}

Did you run `generate_and_validate_chart()` first? Make sure to use the correct chart_filename.
"""

    chart_data = _chart_storage[session_id][chart_filename]
    chart_path = chart_data['file_path']

    if not os.path.exists(chart_path):
        return f"""❌ Chart file not found

**Error:** Chart file does not exist at: {chart_path}

The chart may have been deleted or the session expired.
Please regenerate the chart using `generate_and_validate_chart()`.
"""

    try:
        # 2. Read markdown content
        with open(draft_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 3. Find insertion point
        insertion_point = _find_insertion_point(content, insertion_location)

        if insertion_point is None:
            return f"""❌ Could not find insertion location

**Error:** Could not locate '{insertion_location}' in the document

**Valid formats:**
- "after_executive_summary"
- "dimension:Exact Dimension Name:start"
- "dimension:Exact Dimension Name:middle"
- "dimension:Exact Dimension Name:end"
- "after_paragraph:unique text from paragraph"

Please check the document structure and try again.
"""

        # 4. Copy chart to draft report's charts directory
        # Draft report is in workspace/final/, charts should be in workspace/final/charts/
        draft_dir = os.path.dirname(draft_path)
        charts_dir = os.path.join(draft_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)

        dest_chart_path = os.path.join(charts_dir, chart_filename)
        import shutil
        shutil.copy2(chart_path, dest_chart_path)

        # 5. Create chart insertion WITHOUT figure number (will be auto-assigned)
        # Use placeholder that will be replaced during renumbering
        chart_insertion = f"\n\n![{chart_title}](charts/{chart_filename})\n*Figure X: {chart_description}*\n\n"

        # 6. Insert the chart
        new_content = content[:insertion_point] + chart_insertion + content[insertion_point:]

        # 7. Auto-renumber ALL figures based on document order
        new_content = _renumber_figures_by_position(new_content)

        # 8. Write back to file
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # 9. Upload chart to S3
        s3_upload_status = "Not attempted"
        try:
            import boto3
            from botocore.exceptions import ClientError

            s3_bucket = os.getenv('S3_OUTPUTS_BUCKET')
            if s3_bucket:
                s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-west-2'))
                s3_key = f"research-outputs/{session_id}/charts/{chart_filename}"

                s3_client.upload_file(
                    dest_chart_path,
                    s3_bucket,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'image/png',
                        'ServerSideEncryption': 'AES256'
                    }
                )
                s3_uri = f"s3://{s3_bucket}/{s3_key}"
                s3_upload_status = f"✅ Uploaded to {s3_uri}"
                logger.info(f"Chart uploaded to S3: {s3_uri}")
            else:
                s3_upload_status = "⚠️  S3_OUTPUTS_BUCKET not configured"
                logger.warning("S3_OUTPUTS_BUCKET not set, skipping S3 upload")
        except Exception as s3_error:
            s3_upload_status = f"⚠️  S3 upload failed: {str(s3_error)}"
            logger.error(f"Failed to upload chart to S3: {s3_error}")

        # 10. Find the figure number that was assigned to this chart
        lines_after = new_content.split('\n')
        assigned_figure_num = None
        for i, line in enumerate(lines_after):
            if f'![{chart_title}]' in line and i + 1 < len(lines_after):
                # Next line should have figure caption
                fig_match = re.search(r'\*Figure (\d+):', lines_after[i + 1])
                if fig_match:
                    assigned_figure_num = int(fig_match.group(1))
                    break

        return f"""✅ Chart inserted successfully!

**Figure Number:** {assigned_figure_num if assigned_figure_num else 'Auto-assigned'}
**Title:** {chart_title}
**Location:** {insertion_location}
**File:** charts/{chart_filename}
**S3 Upload:** {s3_upload_status}

The chart has been inserted and all figures have been automatically renumbered in document order.
"""

    except Exception as e:
        import traceback
        return f"""❌ Failed to insert chart

**Error:** {str(e)}

**Traceback:**
```
{traceback.format_exc()}
```
"""


def _find_insertion_point(content: str, location: str) -> int:
    """Find the insertion point in the markdown content based on location string"""
    import re

    # Line number based insertion (new method)
    if location.startswith("line:"):
        try:
            line_num = int(location.split(":")[1])
            lines = content.split('\n')

            # Validate line number
            if line_num < 1 or line_num > len(lines):
                return None

            # Convert line number to character position
            # Insert after the specified line
            char_pos = sum(len(line) + 1 for line in lines[:line_num])  # +1 for newline
            return char_pos
        except (ValueError, IndexError):
            return None

    # After executive summary
    if location == "after_executive_summary":
        exec_summary_pattern = r'(## Executive Summary.*?\n---)'
        match = re.search(exec_summary_pattern, content, re.DOTALL)
        if match:
            return match.end()

    # Dimension-based location
    elif location.startswith("dimension:"):
        parts = location.split(":")
        if len(parts) != 3:
            return None

        _, dimension_name, position = parts

        # Find dimension section: # Dimension Name
        dimension_pattern = rf'(# {re.escape(dimension_name)})'
        match = re.search(dimension_pattern, content)

        if not match:
            return None

        dimension_start = match.end()

        # Find next dimension or end of document
        next_dimension_pattern = r'\n# '
        next_match = re.search(next_dimension_pattern, content[dimension_start:])
        dimension_end = dimension_start + next_match.start() if next_match else len(content)

        dimension_content = content[dimension_start:dimension_end]

        if position == "start":
            # After first paragraph (after first \n\n)
            first_break = dimension_content.find('\n\n')
            if first_break != -1:
                return dimension_start + first_break + 2
            return dimension_start

        elif position == "middle":
            # Middle of dimension section
            return dimension_start + len(dimension_content) // 2

        elif position == "end":
            # Before next dimension or end
            return dimension_end

    # After specific paragraph
    elif location.startswith("after_paragraph:"):
        unique_text = location[len("after_paragraph:"):]

        # Find the paragraph containing this text
        paragraph_idx = content.find(unique_text)
        if paragraph_idx == -1:
            return None

        # Find the end of this paragraph (next \n\n or end of section)
        search_start = paragraph_idx + len(unique_text)
        next_break = content.find('\n\n', search_start)

        if next_break != -1:
            return next_break + 2
        else:
            # Insert at end of document
            return len(content)

    return None


def _renumber_figures_by_position(content: str) -> str:
    """Renumber all figures sequentially based on their position in the document"""
    import re

    lines = content.split('\n')

    # Find all figures: look for image lines followed by caption lines
    figures = []  # List of (line_num, image_line, caption_line)

    i = 0
    while i < len(lines):
        # Check if this is an image line
        if lines[i].startswith('![') and '](charts/' in lines[i]:
            # Check if next line is a figure caption
            if i + 1 < len(lines) and '*Figure' in lines[i + 1]:
                figures.append((i, i + 1))  # Store image and caption line numbers
        i += 1

    # Renumber figures sequentially (1, 2, 3, ...)
    for idx, (img_line, caption_line) in enumerate(figures, start=1):
        # Replace figure number in caption
        old_caption = lines[caption_line]
        new_caption = re.sub(r'\*Figure [X\d]+:', f'*Figure {idx}:', old_caption)
        lines[caption_line] = new_caption

    return '\n'.join(lines)
