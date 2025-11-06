"""Chart Generation Node - Inserts charts directly into markdown

This node analyzes the edited research report and generates appropriate charts,
inserting them directly into the markdown document at optimal locations.

Process:
1. Read the edited markdown document (after editor agent)
2. Analyze each major section
3. Generate appropriate charts (max 1 per section if needed)
4. Insert charts between paragraphs using exact text matching
5. Track chart files in State for later upload to Memory

Key differences from previous version:
- Charts are inserted INTO the markdown (not just generated separately)
- Uses session-isolated paths for chart storage
- Agent uses insert_chart_between_paragraphs tool to place charts
"""

import time
import json
import logging
from typing import Dict, Any
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from src.state import ResearchState
from src.config.llm_config import get_llm_for_node
from src.utils.workspace import get_workspace

logger = logging.getLogger(__name__)
from src.tools.code_interpreter_tool import read_document_lines, generate_and_validate_chart, bring_and_insert_chart
from src.utils.cancellation import check_cancellation


def replace_old_chart_results_with_placeholders(messages, keep_last_n=2):
    """
    Replace old chart generation tool results with placeholders to reduce context size.

    Args:
        messages: List of messages
        keep_last_n: Number of most recent chart results to keep in full

    Returns:
        List of messages with placeholders
    """
    from langchain_core.messages import ToolMessage
    import re

    # Find all ToolMessages from chart generation tools
    chart_tool_indices = []
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            # Check if it's from chart generation tools
            tool_name = getattr(msg, 'name', '')
            if tool_name in ['generate_and_validate_chart', 'bring_and_insert_chart']:
                chart_tool_indices.append(i)

    # Keep only the last N chart tool results in full, replace others with placeholders
    if len(chart_tool_indices) > keep_last_n:
        indices_to_replace = chart_tool_indices[:-keep_last_n]  # All except last N
        logger.debug(f"📝 Replacing {len(indices_to_replace)} old chart tool results with placeholders (keeping last {keep_last_n})")

        new_messages = []
        for i, msg in enumerate(messages):
            if i in indices_to_replace:
                # Replace with placeholder
                tool_name = getattr(msg, 'name', 'unknown')
                # Extract chart name if possible
                content = msg.content if isinstance(msg.content, str) else str(msg.content)

                # Try to find chart name from content
                chart_name = "chart"
                if ".png" in content:
                    # Simple extraction: find first occurrence of *.png
                    match = re.search(r'(\w+\.png)', content)
                    if match:
                        chart_name = match.group(1)

                placeholder = f"✓ Chart operation completed: {chart_name} (details omitted to reduce context size)"

                new_msg = ToolMessage(
                    content=placeholder,
                    tool_call_id=msg.tool_call_id,
                    name=tool_name
                )
                new_messages.append(new_msg)
            else:
                new_messages.append(msg)

        return new_messages

    return messages


def add_cache_point_hook(state):
    """
    Pre-model hook that adds cache points to conversation history.
    This runs BEFORE every LLM call in the ReAct loop.

    Features:
    1. Replaces old chart generation tool results with placeholders (keep only last 2)
       to prevent context explosion
    2. Adds cache point to enable immediate cache write of tool results

    Args:
        state: Current graph state with messages

    Returns:
        Dictionary with llm_input_messages containing messages with cache points
    """
    from langchain_core.messages import ToolMessage

    messages = state.get("messages", [])

    if not messages:
        return {}

    # Step 1: Replace old chart tool results with placeholders
    # Use keep_last_n=1 for more aggressive context reduction (only last chart in full detail)
    messages = replace_old_chart_results_with_placeholders(messages, keep_last_n=1)

    # Step 2: Add cache point to last Human or AI message
    # Find the last Human or AI message (skip Tool messages)
    target_index = -1
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, (HumanMessage, AIMessage)):
            target_index = i
            break

    if target_index == -1:
        return {"llm_input_messages": messages}

    target_message = messages[target_index]

    # Check if cache point already exists
    if isinstance(target_message.content, list):
        has_cache_point = any(
            isinstance(item, dict) and "cachePoint" in item
            for item in target_message.content
        )
        if has_cache_point:
            return {"llm_input_messages": messages}

    # Create new content with cache point
    if isinstance(target_message.content, list):
        new_content = target_message.content + [{"cachePoint": {"type": "default"}}]
    elif isinstance(target_message.content, str):
        new_content = [
            {"text": target_message.content},
            {"cachePoint": {"type": "default"}}
        ]
    else:
        # Unknown format, return as-is
        return {"llm_input_messages": messages}

    # Create NEW message with cache point (preserve all attributes)
    if isinstance(target_message, HumanMessage):
        new_message = HumanMessage(content=new_content, **target_message.dict(exclude={"content", "type"}))
    elif isinstance(target_message, AIMessage):
        new_message = AIMessage(content=new_content, **target_message.dict(exclude={"content", "type"}))
    else:
        return {"llm_input_messages": messages}

    # Return new messages with cache point added
    new_messages = messages[:target_index] + [new_message] + messages[target_index + 1:]

    return {"llm_input_messages": new_messages}


def replace_old_chart_results_hook(state):
    """
    Pre-model hook for non-caching models.
    Only replaces old chart results with placeholders (no cache point).

    Args:
        state: Current graph state with messages

    Returns:
        Dictionary with llm_input_messages
    """
    messages = state.get("messages", [])

    if not messages:
        return {}

    # Replace old chart tool results with placeholders
    # Use keep_last_n=1 for more aggressive context reduction
    messages = replace_old_chart_results_with_placeholders(messages, keep_last_n=1)

    return {"llm_input_messages": messages}


async def chart_generation_node(state: ResearchState) -> Dict[str, Any]:
    """
    Generate and insert charts into the research report markdown.

    This node runs AFTER the editor agent has finalized the markdown content.
    It analyzes the document and inserts visualizations at appropriate locations.

    Args:
        state: ResearchState with:
            - draft_report_file: Path to edited markdown file
            - research_session_id: Session ID for path isolation
            - dimensions: List of research dimensions
            - aspects_by_dimension: Aspect structure

    Returns:
        Dict with chart_files: List of chart metadata for Memory storage
    """
    logger.info("CHART GENERATION started")

    # Check if research is cancelled before starting
    check_cancellation(state)

    start_time = time.time()

    try:
        # Get required state
        draft_report_file = state.get("draft_report_file")
        research_session_id = state.get("research_session_id", "default_session")
        dimensions = state.get("dimensions", [])
        aspects_by_dimension = state.get("aspects_by_dimension", {})
        topic = state.get("topic", "Research")

        if not draft_report_file or not Path(draft_report_file).exists():
            logger.warning("No draft report file found, skipping chart generation")
            return {"chart_files": []}

        # Get workspace for session-isolated chart paths
        workspace = get_workspace()
        charts_dir = workspace.get_session_charts_dir(research_session_id)

        # Only count lines, don't load full content
        with open(draft_report_file, 'r', encoding='utf-8') as f:
            total_lines = len(f.readlines())

        logger.debug(f"Chart generation for document with {total_lines} lines")

        # Get LLM for chart generation
        llm = get_llm_for_node("chart_generation", state)

        # Prepare chart generation tools (3 tools: read + generate + insert)
        chart_tools = [read_document_lines, generate_and_validate_chart, bring_and_insert_chart]

        # System prompt
        system_prompt = f"""Chart generation specialist. Read document, generate charts, and REVIEW image quality before inserting.

**Process:**
1. `read_document_lines(start, end)` - Read 100 lines
2. If chart would add value → `generate_and_validate_chart(code, filename)`
3. **VISUALLY REVIEW** the returned chart image:
   - Clear labels, title, legend?
   - Appropriate colors and contrast?
   - Data clearly visible?
   - Professional appearance?
4. **Decision based on review:**
   - ✅ **High quality** → `bring_and_insert_chart()` to insert
   - ⚠️  **Poor quality but important** → Regenerate with improved code (back to step 2)
   - ❌ **Poor quality and low priority** → Skip, continue to next section
5. Continue reading: `read_document_lines(next_start, next_end)`

**Quality Criteria:**
- Axes labeled clearly
- Title descriptive
- Colors distinguishable
- Text readable
- No overlapping elements
- Professional layout

**Chart Type Ideas (choose based on data):**
- **Bar/Column**: Comparing categories (e.g., market share, revenue by segment)
- **Line**: Trends over time (e.g., stock price, growth rates)
- **Scatter**: Correlations between two variables (e.g., P/E ratio vs growth rate)
- **Pie/Donut**: Composition/proportions (e.g., revenue breakdown, market share)
- **Area**: Cumulative trends (e.g., stacked revenue streams over time)
- **Heatmap**: Matrix data (e.g., correlation matrix, performance across categories)
- **Box plot**: Distribution/variance (e.g., valuation ranges across peers)
- **Horizontal bar**: Ranking with long labels (e.g., company comparisons)

**Rules:**
- Read max 100 lines
- Python: matplotlib, seaborn, pandas, numpy
- `plt.savefig('name.png', dpi=300, bbox_inches='tight')`
- Location: "line:N"
- Max 8 charts

**STOP CONDITIONS (you MUST stop when any is true):**
1. Created 8 charts → STOP immediately
2. Reviewed all major sections → STOP
3. No more data suitable for visualization → STOP
4. Say "I have completed chart generation" and STOP

Document: {total_lines} lines | Session: {research_session_id}"""

        # Check if model supports prompt caching
        model_name = getattr(llm, 'model_id', getattr(llm, 'model', ''))
        supports_caching = any(
            model in model_name for model in [
                'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                'us.anthropic.claude-sonnet-4-20250514-v1:0',
                'us.anthropic.claude-haiku-4-5-20251001-v1:0',
                'anthropic.claude-3-5-haiku-20241022-v1:0'
            ]
        )

        # Create ReAct agent
        if supports_caching:

            # Create system message with cache point
            cached_system_message = SystemMessage(
                content=[
                    {"text": system_prompt},
                    {"cachePoint": {"type": "default"}}
                ]
            )

            # Create custom prompt template with cached system message
            custom_prompt = ChatPromptTemplate.from_messages([
                cached_system_message,
                MessagesPlaceholder(variable_name="messages"),
                MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
            ])

            # Create ReAct agent with cached system prompt and pre-model hook
            chart_agent = create_react_agent(
                model=llm,
                tools=chart_tools,
                prompt=custom_prompt,
                pre_model_hook=add_cache_point_hook,
                checkpointer=MemorySaver()
            )
        else:
            # Create custom prompt with system message
            custom_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
            ])

            # Add pre_model_hook to replace old chart results (no cache point for non-caching models)
            chart_agent = create_react_agent(
                model=llm,
                tools=chart_tools,
                prompt=custom_prompt,
                pre_model_hook=replace_old_chart_results_hook,
                checkpointer=MemorySaver()
            )

        # Prepare user message
        max_charts = 8

        user_message = f"""Create high-quality visualizations for "{topic}" research.

Document: {total_lines} lines | Max: {max_charts} charts

**Your workflow:**
1. Read section: `read_document_lines(1, 100)`
2. If data warrants visualization → Generate chart
3. **REVIEW image carefully** - Check labels, colors, clarity
4. **Decision:**
   - Good quality? → Insert with `bring_and_insert_chart()`
   - Poor but needed? → Regenerate with better code
   - Poor and optional? → Skip, continue reading
5. Read next: `read_document_lines(100, 200)`

**Important:**
- Only insert high-quality, professional charts
- Regenerate if chart has issues (overlapping text, unclear labels, poor colors)
- Skip if chart doesn't add significant value
- **STOP after creating {max_charts} charts or finishing all major sections**

Start by reading lines 1-100!"""

        # Run chart agent with config containing draft file path and session ID
        # Maximum charts: 8 total
        # Each chart requires: read (100 lines at a time) + generate (+ optional regenerate) + insert + reasoning
        # With 100 lines per read: ~6-7 iterations per chart (fewer reads needed)
        # Total iterations needed: 8 charts × 7 calls + exploration = ~56 calls
        recursion_limit = 80  # Plenty of margin (50 was too tight with 50-line reads, 80 is safe with 100-line reads)

        config = {
            "configurable": {
                "draft_report_file": draft_report_file,
                "research_session_id": research_session_id,
                "thread_id": f"chart_gen_{research_session_id}"
            },
            "recursion_limit": recursion_limit
        }


        logger.debug(f"Starting chart agent with recursion_limit={recursion_limit}")

        # Try to invoke agent, handle recursion limit gracefully
        try:
            result = await chart_agent.ainvoke(
                {"messages": [("user", user_message)]},
                config=config
            )
            messages = result.get("messages", [])
        except Exception as e:
            # Check if it's a recursion limit error
            from langgraph.errors import GraphRecursionError
            if isinstance(e, GraphRecursionError):
                logger.warning(f"⚠️  Chart generation reached recursion limit ({recursion_limit})")
                logger.debug("Skipping chart generation and continuing workflow...")
                # Return empty chart_files - workflow continues without charts
                return {"chart_files": []}
            else:
                # Other exceptions - re-raise to be caught by outer try-except
                raise

        # Count tool calls and chart results for logging
        logger.debug(f"Chart agent completed - {len(messages)} messages in conversation")

        tool_call_counts = {}
        charts_created = 0
        charts_failed = 0

        # Analyze tool calls and results (for logging only - S3 upload already done by tool)
        for msg in messages:
            # Count tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    tool_call_counts[tool_name] = tool_call_counts.get(tool_name, 0) + 1

            # Parse tool responses to count successes/failures
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                content = msg.content.strip()

                # Check for successful chart insertion
                if '✅ Chart inserted successfully!' in content:
                    charts_created += 1

                # Check for errors (failure messages)
                elif 'Failed to create chart' in content or 'ERROR' in content:
                    charts_failed += 1

        # Log tool call summary
        if tool_call_counts:
            logger.debug(f"Tool calls made: {tool_call_counts}")
        else:
            logger.warning("No tool calls were made by the chart generation agent")

        # Log final agent message for debugging
        if messages:
            final_msg = messages[-1]
            if hasattr(final_msg, 'content'):
                final_content = str(final_msg.content)[:300]
                logger.debug(f"Agent's final message: {final_content}...")

        elapsed = time.time() - start_time
        logger.info(f"Chart generation completed in {elapsed:.2f}s - {charts_created} charts created, {charts_failed} failed")
        logger.info("✅ Charts uploaded to S3 by bring_and_insert_chart tool")

        # Return empty dict - no need to track chart_files anymore
        # Charts are already uploaded to S3 by the tool
        return {}

    except Exception as e:
        logger.error(f"Chart generation failed: {e}", exc_info=True)
        return {}
