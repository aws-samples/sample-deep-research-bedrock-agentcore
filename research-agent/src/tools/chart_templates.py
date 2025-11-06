"""Chart generation templates for research reports

LLM provides data, templates generate static images for Word/PDF.
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, List, Any
import os
import threading

# Global lock to prevent concurrent chart generation
# Matplotlib is not thread-safe, so we need to serialize chart creation
_chart_generation_lock = threading.Lock()


def generate_research_structure_chart(
    dimensions: List[str],
    aspects_by_dimension: Dict[str, List[str]],
    output_path: str
) -> str:
    """
    Generate hierarchical research structure visualization.

    Args:
        dimensions: List of dimension names
        aspects_by_dimension: Dict mapping dimension to list of aspects
        output_path: Path to save the chart image

    Returns:
        Path to generated image
    """
    import textwrap
    import sys

    # CRITICAL: Use lock to prevent concurrent chart generation with data charts
    with _chart_generation_lock:
        print(f"🎨 Generating research structure chart", file=sys.stderr)
        print(f"   Dimensions: {len(dimensions)}", file=sys.stderr)
        print(f"   Total aspects: {sum(len(aspects) for aspects in aspects_by_dimension.values())}", file=sys.stderr)

        # Calculate figure height based on content
        max_aspects = max(len(aspects) for aspects in aspects_by_dimension.values()) if aspects_by_dimension else 0
        num_dimensions = len(dimensions)
        fig_height = max(8, num_dimensions * 3 + max_aspects * 0.5)

        # Clear any existing plots
        plt.clf()
        plt.close('all')

        fig, ax = plt.subplots(figsize=(14, fig_height))
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        # Modern color palette with better contrast
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']

        # Title
        ax.text(0.5, 0.98, 'Research Structure',
                ha='center', va='top', fontsize=22, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', linewidth=2))

        # Calculate positions with better spacing
        num_dimensions = len(dimensions)
        y_start = 0.92
        total_height = 0.88  # Use more vertical space

        # Calculate space per dimension based on number of aspects
        total_aspects = sum(len(aspects) for aspects in aspects_by_dimension.values())
        dimension_heights = []

        for dimension in dimensions:
            num_aspects = len(aspects_by_dimension.get(dimension, []))
            # Proportional height based on number of aspects
            height_weight = max(0.15, num_aspects / total_aspects) if total_aspects > 0 else 0.15
            dimension_heights.append(height_weight)

        # Normalize heights
        total_weight = sum(dimension_heights)
        dimension_heights = [h / total_weight * total_height for h in dimension_heights]

        current_y = y_start

        for idx, dimension in enumerate(dimensions):
            color = colors[idx % len(colors)]

            # Wrap long dimension names
            wrapped_dim = textwrap.fill(dimension, width=30)
            num_lines = wrapped_dim.count('\n') + 1
            box_height = max(0.08, num_lines * 0.03)

            y_pos = current_y - dimension_heights[idx] / 2

            # Draw dimension box with better styling
            dimension_box = mpatches.FancyBboxPatch(
                (0.05, y_pos - box_height/2), 0.28, box_height,
                boxstyle="round,pad=0.01",
                facecolor=color,
                edgecolor='black',
                linewidth=2,
                alpha=0.85
            )
            ax.add_patch(dimension_box)

            # Multi-line text for dimension
            ax.text(0.19, y_pos, wrapped_dim,
                    ha='center', va='center', fontsize=13, fontweight='bold',
                    color='white', linespacing=1.5)

            # Draw aspects with better layout
            aspects = aspects_by_dimension.get(dimension, [])
            num_aspects = len(aspects)

            if num_aspects > 0:
                # Calculate aspect spacing within this dimension's allocated height
                aspect_height = dimension_heights[idx] * 0.8  # Use 80% of allocated space
                aspect_start_y = current_y - 0.1 * dimension_heights[idx]
                aspect_spacing = aspect_height / num_aspects

                for aspect_idx, aspect in enumerate(aspects):
                    aspect_y = aspect_start_y - (aspect_idx + 0.5) * aspect_spacing
                    aspect_x = 0.55

                    # Draw connecting line with smoother curve
                    from matplotlib.path import Path as MPath
                    from matplotlib.patches import PathPatch

                    # Create curved line
                    verts = [
                        (0.33, y_pos),  # Start from dimension box
                        (0.44, y_pos),  # Control point 1
                        (0.44, aspect_y),  # Control point 2
                        (aspect_x - 0.02, aspect_y)  # End at aspect box
                    ]
                    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4]
                    path = MPath(verts, codes)
                    patch = PathPatch(path, facecolor='none', edgecolor=color,
                                    linewidth=1.5, alpha=0.6)
                    ax.add_patch(patch)

                    # Wrap long aspect names
                    wrapped_aspect = textwrap.fill(aspect, width=45)
                    aspect_lines = wrapped_aspect.count('\n') + 1
                    aspect_box_height = max(0.04, aspect_lines * 0.022)

                    # Draw aspect box with improved styling
                    aspect_box = mpatches.FancyBboxPatch(
                        (aspect_x, aspect_y - aspect_box_height/2), 0.38, aspect_box_height,
                        boxstyle="round,pad=0.008",
                        facecolor='white',
                        edgecolor=color,
                        linewidth=2.5,
                        alpha=0.95
                    )
                    ax.add_patch(aspect_box)

                    # Multi-line text for aspect
                    ax.text(aspect_x + 0.19, aspect_y, wrapped_aspect,
                           ha='center', va='center', fontsize=11,
                           color='#333333', linespacing=1.4)

            current_y -= dimension_heights[idx]

        plt.tight_layout()
        plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')

        # Verify file was saved correctly
        import os
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Research structure chart saved: {output_path} (size: {file_size:,} bytes)", file=sys.stderr)
        else:
            print(f"❌ Research structure chart file not found: {output_path}", file=sys.stderr)

        plt.close()
        return output_path


def generate_data_chart(
    chart_type: str,
    data: List[Dict[str, Any]],
    config: Dict[str, Any],
    output_path: str
) -> str:
    """
    Generate data visualization chart (bar, line, pie, etc.)

    Args:
        chart_type: Type of chart ('bar', 'line', 'pie', 'area')
        data: Chart data (same format as visualization_tool.py)
        config: Chart configuration (title, xAxisKey, etc.)
        output_path: Path to save the chart image

    Returns:
        Path to generated image
    """
    import textwrap
    import sys

    # CRITICAL: Use lock to prevent concurrent chart generation
    # Matplotlib is not thread-safe and will produce corrupted/empty images if called concurrently
    with _chart_generation_lock:
        # Validate input data
        if not data or len(data) == 0:
            error_msg = f"Empty data provided for chart '{config.get('title', 'Unknown')}'"
            print(f"❌ Chart Error: {error_msg}", file=sys.stderr)
            raise ValueError(error_msg)

        print(f"🎨 Generating {chart_type} chart: {config.get('title', 'Unknown')}", file=sys.stderr)
        print(f"   Data points: {len(data)}", file=sys.stderr)
        print(f"   Data: {data}", file=sys.stderr)
        print(f"   Output path: {output_path}", file=sys.stderr)

        # Clear any existing plots to avoid conflicts
        plt.clf()
        plt.close('all')

        # Professional color palette (bright, distinct colors)
        PROFESSIONAL_COLORS = [
            '#5B9BD5',  # Blue
            '#70AD47',  # Green
            '#FFC000',  # Orange
            '#C55A11',  # Dark Orange
            '#ED7D31',  # Light Orange
            '#A5A5A5',  # Gray
            '#4472C4',  # Dark Blue
            '#FF6B6B',  # Red
            '#4ECDC4',  # Teal
            '#FFD93D'   # Yellow
        ]

        fig, ax = plt.subplots(figsize=(12, 7))

        # Set background color
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#F8F9FA')

        # Truncate title if too long
        title = config.get('title', 'Chart')
        if len(title) > 60:
            title = title[:57] + '...'

        if chart_type == 'bar':
            x_key = config.get('xAxisKey')
            y_keys = [k for k in data[0].keys() if k != x_key]

            if not y_keys:
                error_msg = f"No y-axis data found for chart '{title}'. x_key={x_key}, data keys={list(data[0].keys())}"
                print(f"❌ Chart Error: {error_msg}", file=sys.stderr)
                raise ValueError(error_msg)

            x_values = [str(item[x_key]) for item in data]
            y_values = [item[y_keys[0]] for item in data]

            # Validate y_values are numeric
            try:
                y_numeric = [float(y) if not isinstance(y, (int, float)) else y for y in y_values]
            except (ValueError, TypeError) as e:
                error_msg = f"Non-numeric y-axis values in chart '{title}': {y_values}"
                print(f"❌ Chart Error: {error_msg}", file=sys.stderr)
                raise ValueError(error_msg)

            # Assign distinct colors to each bar (cycle through palette)
            bar_colors = [PROFESSIONAL_COLORS[i % len(PROFESSIONAL_COLORS)] for i in range(len(x_values))]

            # Create bars with distinct colors
            bars = ax.bar(x_values, y_numeric, color=bar_colors,
                         edgecolor='white', linewidth=2, alpha=0.9, width=0.7)

            # Add value labels on top of each bar (bold, large font)
            for i, (bar, value) in enumerate(zip(bars, y_numeric)):
                height = bar.get_height()
                # Position label above bar
                label_y = height + (max(y_numeric) - min(y_numeric)) * 0.03
                ax.text(bar.get_x() + bar.get_width()/2., label_y,
                       f'{value:.1f}' if abs(value) < 100 else f'{int(value)}',
                       ha='center', va='bottom',
                       fontsize=13, fontweight='bold', color='#2C3E50')

            # Style improvements
            ax.set_xlabel(x_key.capitalize(), fontsize=13, fontweight='bold', color='#2C3E50')
            ax.set_ylabel(y_keys[0].capitalize(), fontsize=13, fontweight='bold', color='#2C3E50')

            # Tick label styling
            ax.tick_params(axis='both', labelsize=11, colors='#2C3E50')

            # Rotate x-axis labels if they're long
            if len(x_values) > 0 and max(len(str(x)) for x in x_values) > 12:
                plt.xticks(rotation=45, ha='right')

            # Professional grid styling (horizontal only)
            ax.grid(True, alpha=0.2, axis='y', linestyle='-', linewidth=0.8, color='#BDC3C7', zorder=0)
            ax.set_axisbelow(True)

            # Remove top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')

        elif chart_type == 'line':
            x_key = config.get('xAxisKey')
            y_keys = [k for k in data[0].keys() if k != x_key]

            x_values = [str(item[x_key]) for item in data]
            y_values = [item[y_keys[0]] for item in data]

            # Plot line with professional styling
            line = ax.plot(x_values, y_values, marker='o', linewidth=3,
                    color='#5B9BD5', markersize=10, markeredgecolor='white',
                    markeredgewidth=2.5, markerfacecolor='#5B9BD5')

            # Add value labels at each point (bold, large font)
            for i, (x, y) in enumerate(zip(x_values, y_values)):
                ax.text(i, y, f'{y:.1f}' if abs(y) < 100 else f'{int(y)}',
                       ha='center', va='bottom', fontsize=12, fontweight='bold',
                       color='#2C3E50', bbox=dict(boxstyle='round,pad=0.4',
                       facecolor='white', edgecolor='#BDC3C7', linewidth=1, alpha=0.9))

            # Style improvements
            ax.set_xlabel(x_key.capitalize(), fontsize=13, fontweight='bold', color='#2C3E50')
            ax.set_ylabel(y_keys[0].capitalize(), fontsize=13, fontweight='bold', color='#2C3E50')

            # Tick label styling
            ax.tick_params(axis='both', labelsize=11, colors='#2C3E50')

            # Professional grid styling
            ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.8, color='#BDC3C7', zorder=0)
            ax.set_axisbelow(True)

            # Remove top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')

            # Rotate x-axis labels if they're long
            if len(x_values) > 0 and max(len(str(x)) for x in x_values) > 12:
                plt.xticks(rotation=45, ha='right')

        elif chart_type == 'pie':
            segments = [item.get('segment', item.get('name', '')) for item in data]
            values = [item.get('value', item.get('count', 0)) for item in data]

            # Use professional color palette
            pie_colors = [PROFESSIONAL_COLORS[i % len(PROFESSIONAL_COLORS)] for i in range(len(segments))]

            # Create pie chart with professional styling
            wedges, texts, autotexts = ax.pie(values, autopct='%1.1f%%',
                   colors=pie_colors, startangle=90,
                   textprops={'fontsize': 12, 'weight': 'bold', 'color': 'white'},
                   wedgeprops={'edgecolor': 'white', 'linewidth': 2})

            # Make percentage text more readable
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(12)
                autotext.set_weight('bold')

            # Add legend with full labels (professional styling)
            ax.legend(wedges, segments, title="Categories", loc="center left",
                     bbox_to_anchor=(1, 0, 0.5, 1), fontsize=11, frameon=True,
                     fancybox=True, shadow=False, title_fontsize=12,
                     edgecolor='#BDC3C7', framealpha=0.95)

        elif chart_type == 'area':
            x_key = config.get('xAxisKey')
            y_keys = [k for k in data[0].keys() if k != x_key]

            x_values = [str(item[x_key]) for item in data]
            y_values = [item[y_keys[0]] for item in data]

            # Convert x_values to numeric indices for fill_between to work properly
            x_indices = range(len(x_values))

            # Area fill with professional styling
            ax.fill_between(x_indices, y_values, alpha=0.3, color='#5B9BD5', zorder=1)
            ax.plot(x_indices, y_values, linewidth=3, color='#5B9BD5',
                    marker='o', markersize=10, markeredgecolor='white',
                    markeredgewidth=2.5, markerfacecolor='#5B9BD5', zorder=2)

            # Add value labels at each point (bold, large font)
            for i, y in enumerate(y_values):
                ax.text(i, y, f'{y:.1f}' if abs(y) < 100 else f'{int(y)}',
                       ha='center', va='bottom', fontsize=12, fontweight='bold',
                       color='#2C3E50', bbox=dict(boxstyle='round,pad=0.4',
                       facecolor='white', edgecolor='#BDC3C7', linewidth=1, alpha=0.9))

            # Set x-tick labels
            ax.set_xticks(x_indices)
            ax.set_xticklabels(x_values)

            # Style improvements
            ax.set_xlabel(x_key.capitalize(), fontsize=13, fontweight='bold', color='#2C3E50')
            ax.set_ylabel(y_keys[0].capitalize(), fontsize=13, fontweight='bold', color='#2C3E50')

            # Tick label styling
            ax.tick_params(axis='both', labelsize=11, colors='#2C3E50')

            # Professional grid styling
            ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.8, color='#BDC3C7', zorder=0)
            ax.set_axisbelow(True)

            # Remove top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')

            # Rotate x-axis labels if they're long
            if len(x_values) > 0 and max(len(str(x)) for x in x_values) > 12:
                plt.xticks(rotation=45, ha='right')

        # Set title with professional styling
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20, color='#2C3E50')

        # Use tight_layout with padding to prevent title clipping
        plt.tight_layout(pad=2.5)
        plt.savefig(output_path, dpi=200, bbox_inches='tight', pad_inches=0.4, facecolor='white')

        # Verify file was saved correctly
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Chart saved: {output_path} (size: {file_size:,} bytes)", file=sys.stderr)
        else:
            print(f"❌ Chart file not found: {output_path}", file=sys.stderr)

        plt.close()
        return output_path


def generate_workflow_diagram(
    stages: List[str],
    current_stage: str,
    output_path: str
) -> str:
    """
    Generate workflow progress diagram.

    Args:
        stages: List of workflow stage names
        current_stage: Currently active stage
        output_path: Path to save the chart image

    Returns:
        Path to generated image
    """
    import textwrap

    num_stages = len(stages)

    # Vertical layout for better readability
    fig_height = max(8, num_stages * 1.5)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.axis('off')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Title
    ax.text(0.5, 0.98, 'Workflow Progress',
            ha='center', va='top', fontsize=20, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', linewidth=2))

    # Calculate vertical spacing
    y_start = 0.90
    y_spacing = 0.80 / num_stages

    current_stage_idx = stages.index(current_stage) if current_stage in stages else -1

    for idx, stage in enumerate(stages):
        y_pos = y_start - (idx * y_spacing)

        # Determine status and styling
        if idx < current_stage_idx:
            color = '#4ECDC4'  # Completed - teal
            status_symbol = '✓'
            border_width = 2
            alpha = 0.9
        elif idx == current_stage_idx:
            color = '#45B7D1'  # Current - blue
            status_symbol = '▶'
            border_width = 3
            alpha = 1.0
        else:
            color = '#E8E8E8'  # Pending - light gray
            status_symbol = '○'
            border_width = 2
            alpha = 0.7

        # Wrap long stage names
        wrapped_stage = textwrap.fill(stage, width=25)
        num_lines = wrapped_stage.count('\n') + 1
        box_height = max(0.10, num_lines * 0.05)

        # Draw stage box with shadow effect for current stage
        if idx == current_stage_idx:
            # Shadow
            shadow_box = mpatches.FancyBboxPatch(
                (0.12, y_pos - box_height/2 - 0.005), 0.76, box_height,
                boxstyle="round,pad=0.015",
                facecolor='gray',
                alpha=0.3,
                zorder=1
            )
            ax.add_patch(shadow_box)

        # Main box
        stage_box = mpatches.FancyBboxPatch(
            (0.10, y_pos - box_height/2), 0.76, box_height,
            boxstyle="round,pad=0.015",
            facecolor=color,
            edgecolor='black',
            linewidth=border_width,
            alpha=alpha,
            zorder=2
        )
        ax.add_patch(stage_box)

        # Stage number circle
        circle = plt.Circle((0.16, y_pos), 0.025, color='white',
                           edgecolor='black', linewidth=2, zorder=3)
        ax.add_patch(circle)
        ax.text(0.16, y_pos, str(idx + 1),
               ha='center', va='center', fontsize=13, fontweight='bold', zorder=4)

        # Status symbol
        symbol_color = 'white' if idx <= current_stage_idx else '#666666'
        ax.text(0.82, y_pos, status_symbol,
               ha='center', va='center', fontsize=20,
               fontweight='bold', color=symbol_color, zorder=3)

        # Stage name
        text_color = 'white' if idx <= current_stage_idx else '#333333'
        ax.text(0.48, y_pos, wrapped_stage,
               ha='center', va='center', fontsize=14,
               color=text_color, fontweight='bold', linespacing=1.4, zorder=3)

        # Draw arrow to next stage
        if idx < num_stages - 1:
            arrow_y = y_pos - box_height/2 - 0.02
            arrow_length = y_spacing - box_height - 0.04

            # Draw arrow with thicker style
            ax.annotate('', xy=(0.48, arrow_y - arrow_length),
                       xytext=(0.48, arrow_y),
                       arrowprops=dict(arrowstyle='->', lw=2.5, color='#666666'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path
