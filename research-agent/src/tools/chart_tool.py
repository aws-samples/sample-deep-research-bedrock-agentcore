"""Chart generation tool for research reports

Agent provides chart definition, tool generates static image.
"""

from langchain.tools import tool
from typing import Annotated, Dict, Any, List
from langchain_core.runnables import RunnableConfig
import json
import os
from pathlib import Path


@tool
def create_and_insert_research_structure_chart(
    dimensions: List[str],
    aspects_by_dimension: Dict[str, List[str]],
    chart_title: str,
    config: Annotated[RunnableConfig, "Injected configuration"]
) -> str:
    """Create research structure chart and automatically insert it into the document.

    This tool generates a hierarchical visualization and inserts it after the Executive Summary.
    No need to call insert_chart separately - this does both in one step!

    Args:
        dimensions: List of dimension names (e.g., ["Technical Analysis", "Market Analysis"])
        aspects_by_dimension: Dict mapping each dimension to its aspects
            Example: {
                "Technical Analysis": ["Performance Metrics", "Architecture"],
                "Market Analysis": ["Competition", "Trends"]
            }
        chart_title: Title for the chart

    Returns:
        JSON string with success/error status and figure number
    """
    from src.tools.chart_templates import generate_research_structure_chart
    from src.utils.workspace import get_workspace
    import re

    # Get session ID and draft path from config
    session_id = config.get("configurable", {}).get("research_session_id", "default_session")
    draft_path = config.get("configurable", {}).get("draft_report_file")

    if not draft_path:
        return json.dumps({"status": "error", "message": "No draft_report_file in config"})

    try:
        # 1. Generate chart file
        workspace = get_workspace()
        output_path = workspace.get_chart_path(session_id, "research_structure.png")
        generate_research_structure_chart(dimensions, aspects_by_dimension, output_path)

        # 2. Read markdown content
        with open(draft_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 3. Find insertion point (after Executive Summary section)
        # Look for pattern: ## Executive Summary\n...\n---
        exec_summary_pattern = r'(## Executive Summary.*?\n---)'
        match = re.search(exec_summary_pattern, content, re.DOTALL)

        if not match:
            return json.dumps({
                "status": "error",
                "message": "Could not find Executive Summary section"
            })

        insertion_point = match.end()

        # 4. Auto-increment figure number
        figure_numbers = re.findall(r'\*Figure (\d+):', content)
        next_figure_num = max([int(n) for n in figure_numbers], default=0) + 1

        # 5. Create chart insertion with caption
        chart_insertion = f"\n\n![Research Structure](charts/research_structure.png)\n*Figure {next_figure_num}: {chart_title}*\n"

        # 6. Insert the chart
        new_content = content[:insertion_point] + chart_insertion + content[insertion_point:]

        # 7. Write back to file
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return json.dumps({
            "status": "success",
            "message": f"Research structure chart created and inserted as Figure {next_figure_num}",
            "figure_number": next_figure_num,
            "chart_path": "charts/research_structure.png",
            "file_path": output_path
        }, indent=2)

    except Exception as e:
        import sys
        import traceback
        print(f"\n❌ ERROR in create_and_insert_research_structure_chart:", file=sys.stderr)
        print(f"   {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "status": "error",
            "message": f"Failed to create and insert chart: {str(e)}"
        })


@tool
def create_and_insert_data_chart(
    chart_type: str,
    data: List[Dict[str, Any]],
    title: str,
    description: str,
    dimension_name: str,
    position: str,
    x_axis_key: str,
    config: Annotated[RunnableConfig, "Injected configuration"]
) -> str:
    """Create data chart and automatically insert it into a dimension section.

    This tool generates a data visualization and inserts it into the specified dimension section.
    No need to call insert_chart separately - this does both in one step!

    Args:
        chart_type: Type of chart - MUST be one of: 'bar', 'line', 'pie', 'area'

        data: List of data dictionaries. Structure MUST match chart_type:

            For 'bar', 'line', 'area' charts:
              [{"<x_axis_key>": "Label1", "value": 100},
               {"<x_axis_key>": "Label2", "value": 150}]
              - MUST have x_axis_key matching the x_axis_key parameter
              - MUST have "value" key with NUMERIC data
              - Example: [{"metric": "Latency", "value": 42}, {"metric": "Cost", "value": 78}]

            For 'pie' charts:
              [{"segment": "Category1", "value": 30},
               {"segment": "Category2", "value": 70}]
              - MUST have "segment" key for labels
              - MUST have "value" key with NUMERIC data (percentages or counts)
              - Example: [{"segment": "AWS", "value": 45}, {"segment": "Azure", "value": 35}]

        title: Chart title (will be shown at top of chart, max 50 chars recommended)

        description: Brief description explaining the insight (used as Figure caption below chart)

        dimension_name: EXACT name of the dimension heading to insert chart into
                       Must match a "# Dimension Name" heading in the document
                       Example: "Cost Tracking and Optimization Integration"

        position: Where to place chart in the dimension section:
                 - 'start': After the dimension introduction paragraph
                 - 'end': Before the next dimension section begins

        x_axis_key: Name of the key in data dictionaries to use for x-axis labels
                   MUST match the key in your data dictionaries
                   For pie charts, this parameter is ignored (always uses "segment")
                   Example: If data is [{"metric": "...", "value": ...}], use "metric"

    Returns:
        JSON string with success/error status and figure number

    CRITICAL REQUIREMENTS:
    - All "value" fields in data MUST be numeric (int or float), NOT strings
    - Minimum 3 data points required for meaningful charts
    - x_axis_key must exactly match the key name in your data dictionaries
    - dimension_name must exactly match a dimension heading in the document

    Examples:
        # Bar chart comparing metrics
        create_and_insert_data_chart(
            chart_type="bar",
            data=[
                {"metric": "Latency", "value": 150},
                {"metric": "Throughput", "value": 85},
                {"metric": "Cost", "value": 42}
            ],
            title="System Performance Metrics",
            description="Comparison of key performance indicators",
            dimension_name="Performance Analysis",
            position="start",
            x_axis_key="metric"  # Matches the key in data dicts
        )

        # Pie chart for distribution
        create_and_insert_data_chart(
            chart_type="pie",
            data=[
                {"segment": "Training", "value": 45},
                {"segment": "Inference", "value": 35},
                {"segment": "Storage", "value": 20}
            ],
            title="Cost Distribution",
            description="Breakdown of operational costs by category",
            dimension_name="Cost Analysis",
            position="end",
            x_axis_key="segment"  # For pie, always use "segment"
        )
    """
    from src.tools.chart_templates import generate_data_chart
    from src.utils.workspace import get_workspace
    import re

    # Validate chart_type
    valid_types = ['bar', 'line', 'pie', 'area']
    if chart_type not in valid_types:
        return json.dumps({
            "status": "error",
            "message": f"Invalid chart_type. Must be one of: {', '.join(valid_types)}"
        })

    # Validate position
    if position not in ['start', 'end']:
        return json.dumps({
            "status": "error",
            "message": "position must be 'start' or 'end'"
        })

    # Get session ID and draft path from config
    session_id = config.get("configurable", {}).get("research_session_id", "default_session")
    draft_path = config.get("configurable", {}).get("draft_report_file")

    if not draft_path:
        return json.dumps({"status": "error", "message": "No draft_report_file in config"})

    try:
        # 1. Generate chart file
        workspace = get_workspace()
        safe_filename = title.lower().replace(' ', '_').replace('/', '_')[:50]
        output_path = workspace.get_chart_path(session_id, f"{safe_filename}.png")

        chart_config = {
            'title': title,
            'description': description,
            'xAxisKey': x_axis_key
        }
        generate_data_chart(chart_type, data, chart_config, output_path)

        # 2. Read markdown content
        with open(draft_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 3. Find dimension section
        # Pattern: # Dimension Name\n...\n---\n(next section or end)
        # Stop before: next dimension (#), Conclusion (##), or document end
        dimension_pattern = rf'(# {re.escape(dimension_name)}.*?)(?=\n---\n(?:## Conclusion|#)|\Z)'
        match = re.search(dimension_pattern, content, re.DOTALL)

        if not match:
            return json.dumps({
                "status": "error",
                "message": f"Could not find dimension section: {dimension_name}"
            })

        section_start = match.start()
        section_end = match.end()
        section_content = match.group(1)

        # 4. Determine insertion point within section
        if position == 'start':
            # Insert after the ## Introduction paragraph (after first \n\n)
            intro_end = section_content.find('\n\n', section_content.find('## Introduction'))
            if intro_end != -1:
                insertion_point = section_start + intro_end + 2
            else:
                # Fallback: insert after dimension title
                insertion_point = section_start + section_content.find('\n\n') + 2
        else:  # position == 'end'
            # Insert before the section ends (before --- or next #)
            insertion_point = section_end

        # 5. Auto-increment figure number
        figure_numbers = re.findall(r'\*Figure (\d+):', content)
        next_figure_num = max([int(n) for n in figure_numbers], default=0) + 1

        # 6. Create chart insertion with caption
        chart_insertion = f"\n\n![{title}](charts/{safe_filename}.png)\n*Figure {next_figure_num}: {description}*\n\n"

        # 7. Insert the chart
        new_content = content[:insertion_point] + chart_insertion + content[insertion_point:]

        # 8. Write back to file
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return json.dumps({
            "status": "success",
            "message": f"Data chart '{title}' created and inserted as Figure {next_figure_num}",
            "figure_number": next_figure_num,
            "chart_path": f"charts/{safe_filename}.png",
            "file_path": output_path,
            "dimension": dimension_name,
            "position": position
        }, indent=2)

    except Exception as e:
        import sys
        import traceback
        print(f"\n❌ ERROR in create_and_insert_data_chart:", file=sys.stderr)
        print(f"   Chart: {title}", file=sys.stderr)
        print(f"   Error: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "status": "error",
            "message": f"Failed to create and insert chart: {str(e)}"
        })


@tool
def create_workflow_diagram(
    stages: List[str],
    current_stage: str,
    config: Annotated[RunnableConfig, "Injected configuration"]
) -> str:
    """Create a workflow progress diagram showing research stages.

    Best for: Showing research process and current progress.

    Args:
        stages: List of workflow stage names in order
        current_stage: Name of the currently active stage

    Returns:
        JSON string with chart file path and metadata
    """
    from src.tools.chart_templates import generate_workflow_diagram
    from src.utils.workspace import get_workspace

    # Get session ID from config
    session_id = config.get("configurable", {}).get("research_session_id", "default_session")
    draft_path = config.get("configurable", {}).get("draft_report_file")

    if not draft_path:
        return json.dumps({"error": "No draft_report_file in config"})

    # Use workspace session-isolated chart path
    workspace = get_workspace()
    output_path = workspace.get_chart_path(session_id, "workflow_diagram.png")

    # Generate chart
    generate_workflow_diagram(stages, current_stage, output_path)

    return json.dumps({
        "status": "success",
        "chart_type": "workflow_diagram",
        "file_path": output_path,
        "title": "Research Workflow",
        "markdown": "![Research Workflow](charts/workflow_diagram.png)"
    }, indent=2)


@tool
def insert_chart_between_paragraphs(
    before_text: str,
    chart_path: str,
    chart_caption: str,
    config: Annotated[RunnableConfig, "Injected configuration"]
) -> str:
    """Insert a chart after a specific paragraph using exact text matching.

    This tool inserts a chart immediately after a paragraph identified by its
    exact text content. Much simpler and more reliable than matching two texts.

    Args:
        before_text: Exact text of the last sentence of the paragraph BEFORE the chart.
                    Must match exactly including punctuation.
                    Chart will be inserted immediately after this text.
        chart_path: Relative path to the chart image (e.g., "charts/chart_001.png")
        chart_caption: Caption for the chart (1-2 sentences explaining what it shows)

    Returns:
        JSON string indicating success or error with details

    Example:
        before_text: "This analysis reveals key performance trends."
        chart_path: "charts/performance_trend.png"
        chart_caption: "Performance metrics across different model configurations."
    """
    import json

    # Get markdown file from config
    draft_path = config.get("configurable", {}).get("draft_report_file")
    if not draft_path:
        return json.dumps({
            "status": "error",
            "message": "No draft_report_file in config"
        })

    try:
        # Read current markdown content
        with open(draft_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the insertion point using exact text matching
        before_index = content.find(before_text)

        if before_index == -1:
            return json.dumps({
                "status": "error",
                "message": f"Could not find exact match for before_text: '{before_text[:80]}...'"
            })

        # Calculate insertion point (after before_text)
        insertion_point = before_index + len(before_text)

        # Auto-increment figure number
        import re
        figure_numbers = re.findall(r'\*Figure (\d+):', content)
        next_figure_num = max([int(n) for n in figure_numbers], default=0) + 1

        # Create chart insertion with caption
        chart_insertion = f"\n\n![Chart]({chart_path})\n*Figure {next_figure_num}: {chart_caption}*\n\n"

        # Insert the chart
        new_content = (
            content[:insertion_point] +
            chart_insertion +
            content[insertion_point:]
        )

        # Write back to file
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return json.dumps({
            "status": "success",
            "message": f"Chart inserted successfully as Figure {next_figure_num}",
            "figure_number": next_figure_num,
            "chart_path": chart_path
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to insert chart: {str(e)}"
        })


@tool
def insert_chart_to_markdown(
    markdown_reference: str,
    position: str,
    config: Annotated[RunnableConfig, "Injected configuration"]
) -> str:
    """Insert a chart into the markdown document.

    Args:
        markdown_reference: Markdown image reference (e.g., "![Title](path/to/chart.png)")
        position: Where to insert ('after_title', 'after_summary', 'before_conclusion', 'end')

    Returns:
        JSON string with operation result
    """
    # Get draft path from config
    draft_path = config.get("configurable", {}).get("draft_report_file")
    if not draft_path:
        return json.dumps({"error": "No draft_report_file in config"})

    # Read current content
    with open(draft_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Determine insertion point
    if position == 'after_title':
        # Insert after first heading
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# '):
                lines.insert(i + 2, f'\n{markdown_reference}\n')
                break
        content = '\n'.join(lines)

    elif position == 'after_summary':
        # Insert after Executive Summary section
        content = content.replace(
            '## Executive Summary',
            f'## Executive Summary\n\n{markdown_reference}\n',
            1
        )

    elif position == 'before_conclusion':
        # Insert before Conclusion section
        content = content.replace(
            '## Conclusion',
            f'\n{markdown_reference}\n\n## Conclusion',
            1
        )

    elif position == 'end':
        # Insert at end
        content += f'\n\n{markdown_reference}\n'

    # Write back
    with open(draft_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return json.dumps({
        "status": "success",
        "message": f"Chart inserted at position: {position}"
    }, indent=2)
