#!/usr/bin/env python3
"""Generate workflow diagram for dimensional research agent."""

import os
import sys
from pathlib import Path
import nest_asyncio

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.workflow import create_workflow
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

# Apply nest_asyncio for async functions
nest_asyncio.apply()


def main():
    """Generate and save workflow diagram."""

    try:
        # Create workflow
        print("Creating dimensional research workflow...")
        app = create_workflow()

        # Generate PNG using Pyppeteer (local browser rendering)
        print("\nGenerating workflow diagram...")
        png_data = app.get_graph().draw_mermaid_png(
            curve_style=CurveStyle.LINEAR,
            node_colors=NodeStyles(
                first="#ffdfba",      # Orange for START
                last="#baffc9",       # Green for END
                default="#fad7de"     # Pink for processing nodes
            ),
            wrap_label_n_words=9,
            draw_method=MermaidDrawMethod.PYPPETEER,
            background_color="white",
            padding=10,
        )

        # Save PNG file to project root
        output_path = project_root / "dimensional_research_workflow.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✅ Workflow diagram saved to: {output_path}")

        # Also save mermaid code for reference
        mermaid_code = app.get_graph().draw_mermaid()
        mermaid_path = project_root / "dimensional_research_workflow.mmd"
        with open(mermaid_path, "w") as f:
            f.write(mermaid_code)
        print(f"✅ Mermaid code saved to: {mermaid_path}")

        # Print workflow summary
        print("\n" + "="*80)
        print("DIMENSIONAL RESEARCH WORKFLOW SUMMARY")
        print("="*80)
        print("\n📊 3-Stage Research Pipeline:")
        print("\n  Stage 1: Topic Analysis (Sequential)")
        print("    └─ topic_analysis: Identify key research dimensions")
        print("       • Uses: Simple LLM with structured output")
        print("       • Tools: DuckDuckGo web search")
        print("       • Output: 3-5 dimensions")

        print("\n  Stage 2: Aspect Analysis (Parallel)")
        print("    └─ aspect_analysis × N: Identify aspects per dimension")
        print("       • Uses: Simple LLM with structured output")
        print("       • Execution: PARALLEL for each dimension")
        print("       • Tools: DuckDuckGo web search")
        print("       • Output: 3 aspects per dimension")

        print("\n  Stage 3: Deep Research (Parallel)")
        print("    └─ research × N×3: Conduct deep research per aspect")
        print("       • Uses: ReAct Agent with tool calling")
        print("       • Execution: PARALLEL for each aspect")
        print("       • Tools: ArXiv search + paper retrieval")
        print("       • Output: Research findings with citations")

        print("\n  Finalization:")
        print("    └─ finalize: Aggregate and summarize results")

        print("\n🔑 Key Features:")
        print("  • Map-Reduce pattern with Send API for parallelization")
        print("  • State reducers (merge_dicts) for combining parallel results")
        print("  • Mixed approach: Simple LLM for extraction, ReAct for research")
        print("  • Efficient: Stages 2 and 3 execute in parallel")

        print("\n📈 Execution Flow:")
        print("  1→N: Topic Analysis fans out to N aspect analyses")
        print("  N→N×3: Each dimension fans out to 3 research tasks")
        print("  N×3→1: All research converges to final report")

        print("\n" + "="*80)

    except Exception as e:
        print(f"\n❌ Error generating workflow diagram: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
