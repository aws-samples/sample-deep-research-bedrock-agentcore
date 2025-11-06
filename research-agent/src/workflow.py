"""Main workflow definition for dimensional research

Unified workflow with sequential reference processing and parallel research:
1. START → initialize_session
2. initialize_session → reference_preparation (if references provided, sequential) OR topic_analysis (skip if no references)
3. reference_preparation → topic_analysis (sequential: references inform topic analysis)
4. topic_analysis → aspect_analysis (parallel by dimension)
5. aspect_analysis → prepare_research (barrier: wait for all dimensions)
6. prepare_research → research_planning (unified refinement + reference integration, runs once)
7. research_planning → research (parallel by aspect)
8. research → prepare_dimension_reduction (barrier)
9. prepare_dimension_reduction → dimension_reduction (parallel by dimension) - Creates markdown docs
10. dimension_reduction → report_writing (barrier, merge dimensions + edit + summary/conclusion → final markdown)
11. report_writing → chart_generation (generate and insert charts into markdown)
12. chart_generation → document_conversion (convert markdown to Word + PDF)
13. document_conversion → finalize → END
"""

import time
import logging
from datetime import datetime
from typing import List, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from src.state import ResearchState
from src.nodes.reference_preparation import reference_preparation_node
from src.nodes.research_planning import research_planning_node
from src.nodes.topic_analysis import topic_analysis_node
from src.nodes.aspect_analysis import aspect_analysis_node
from src.nodes.research_agent import research_agent_node
from src.nodes.dimension_reduction import dimension_reduction_node
from src.nodes.report_writing import report_writing_node
from src.nodes.chart_generation import chart_generation_node
from src.nodes.document_conversion import document_conversion_node
from src.utils.logger import get_module_logger

# Initialize logger
logger = get_module_logger(__name__)


def initialize_session(state: ResearchState) -> dict:
    """
    Initialize session: Use session ID from caller, log session start, extract research context.

    This node runs first and updates the state with session_id and research_context.
    """
    try:
        from src.utils.session_logger import get_session_logger
        from src.utils.status_updater import set_status_updater

        config = state.get("research_config", {})
        research_context = config.get("research_context")
        topic = state.get("topic", "research")

        # Use session ID from caller (passed via bff_session_id)
        session_id = state.get("bff_session_id")
        logger.info(f"🔑 Research Session ID: {session_id}")
        logger.info(f"Topic: {topic}")
        logger.info(f"Research Type: {config.get('research_type', 'basic_web')}")
        logger.info(f"Model: {config.get('llm_model', 'unknown')}")
        logger.info(f"Research Depth: {config.get('research_depth', 'balanced')}")

        # Initialize DynamoDB status updater
        status_updater = set_status_updater(session_id)
        status_updater.mark_processing()  # Set status='processing' so frontend keeps polling
        status_updater.update_stage('initialize_session')

        # Store topic, model, and research_depth in DynamoDB for UI display
        status_updater.update(
            topic=topic,
            research_type=config.get("research_type", "basic_web"),
            model=config.get("llm_model", "unknown"),
            research_depth=config.get("research_depth", "balanced"),
            research_context=research_context if research_context else None
        )

        # Log session start
        session_logger = get_session_logger()
        session_logger.log_session_start(
            session_id=session_id,
            topic=topic,
            research_config=config,
            research_context=research_context
        )

        # Log research start event to AgentCore Memory
        from src.utils.event_tracker import get_event_tracker
        user_id = state.get("user_id")
        if not user_id:
            logger.warning("⚠️  user_id not found in state - event tracking may fail")

        event_tracker = get_event_tracker()
        if event_tracker and user_id:
            event_tracker.log_research_start(
                session_id=session_id,
                topic=topic,
                config=config,
                actor_id=user_id
            )

        # Update state with session_id and research_context
        updates = {"research_session_id": session_id}
        if research_context:
            updates["research_context"] = research_context

        logger.info("✅ Session initialized successfully")
        return updates

    except Exception as e:
        logger.error(f"Error in initialize_session: {e}", exc_info=True)
        raise


def route_from_start(state: ResearchState) -> Literal["reference_preparation", "topic_analysis"]:
    """
    Sequential routing: Check if references exist.

    - If references exist: go to reference_preparation first
    - If no references: skip directly to topic_analysis

    This ensures reference results are available before topic/aspect analysis.
    """
    try:
        config = state.get("research_config", {})
        references_config = config.get("reference_materials", [])

        if references_config:
            logger.info("📚 References provided - starting reference preparation first (sequential)")
            return "reference_preparation"
        else:
            logger.info("🔍 No references - proceeding directly to topic analysis")
            return "topic_analysis"

    except Exception as e:
        logger.error(f"Error in route_from_start: {e}", exc_info=True)
        return "topic_analysis"  # Default to topic_analysis on error




def continue_to_aspect_analysis(state: ResearchState) -> List[Send]:
    """
    Fan-out: Create parallel tasks for aspect analysis.

    Each dimension gets its own aspect_analysis_node execution.
    Note: reference_preparation now runs sequentially before topic_analysis,
    so reference results are already available in state.
    """
    try:
        dimensions = state.get("dimensions", [])
        topic = state.get("topic", "")
        reference_materials = state.get("reference_materials", [])
        research_config = state.get("research_config", {})
        research_context = state.get("research_context", "")

        logger.info("="*80)
        logger.info("STAGE 2: ASPECT ANALYSIS (Parallel)")
        logger.info("="*80)
        logger.info(f"Topic: {topic[:100]}...")
        logger.info(f"Dimensions: {dimensions}")

        # Validate dimensions
        if not dimensions:
            logger.error("No dimensions found in state! Cannot continue to aspect_analysis.")
            logger.error(f"State keys: {list(state.keys())}")
            return []

        # Create parallel tasks
        sends = []

        # Add aspect_analysis tasks (parallel by dimension)
        for dimension in dimensions:
            sends.append(
                Send(
                    "aspect_analysis",
                    {
                        "dimension": dimension,
                        "topic": topic,
                        "reference_materials": reference_materials,
                        "research_config": research_config,
                        "research_context": research_context
                    }
                )
            )
            logger.debug(f"Created Send for dimension: {dimension}")

        logger.info(f"📤 Fanning out to {len(dimensions)} parallel aspect analysis tasks...")
        logger.info(f"Created {len(sends)} Send objects")

        return sends

    except Exception as e:
        logger.error(f"Error in continue_to_aspect_analysis: {e}", exc_info=True)
        return []


def continue_to_research(state: ResearchState) -> List[Send]:
    """
    Fan-out: Create parallel tasks for research.

    Each aspect within each dimension gets its own research_agent_node execution.
    Only sends incomplete aspects (completed=False) to research.
    """
    aspects_by_dimension = state.get("aspects_by_dimension", {})
    topic = state.get("topic", "")
    research_config = state.get("research_config", {})
    reference_materials = state.get("reference_materials", [])
    research_context = state.get("research_context", "")
    research_session_id = state.get("research_session_id", "default_session")
    user_id = state.get("user_id")  # Get user_id from state

    print(f"\n{'='*80}")
    print(f"STAGE 3: DEEP RESEARCH (Parallel)")
    print(f"{'='*80}")

    # Debug: Check state received from research_planning
    print(f"\n🔍 State Debug (from research_planning):")
    print(f"   aspects_by_dimension: {list(aspects_by_dimension.keys()) if aspects_by_dimension else 'None/Empty'}")
    if aspects_by_dimension:
        for dim, aspects in aspects_by_dimension.items():
            print(f"      {dim}: {len(aspects)} aspects")

    # Count total aspects and filter incomplete ones
    total_aspects = sum(len(aspects) for aspects in aspects_by_dimension.values())
    incomplete_aspects = []
    completed_aspects = []

    for dimension, aspects in aspects_by_dimension.items():
        for aspect in aspects:
            if aspect.get("completed", False):
                completed_aspects.append(f"{dimension}::{aspect['name']}")
            else:
                incomplete_aspects.append((dimension, aspect))

    print(f"\n📊 Total aspects: {total_aspects}")
    print(f"   ✅ Already covered by references: {len(completed_aspects)}")
    print(f"   🔍 Need additional research: {len(incomplete_aspects)}")

    if completed_aspects:
        print(f"\n📚 Skipping research for {len(completed_aspects)} completed aspect(s):")
        for aspect_key in completed_aspects[:5]:
            print(f"      ✅ {aspect_key}")
        if len(completed_aspects) > 5:
            print(f"      ... and {len(completed_aspects) - 5} more")

    print(f"\n📤 Fanning out to {len(incomplete_aspects)} parallel research tasks...")

    # Create parallel tasks only for incomplete aspects
    sends = []
    for dimension, aspect in incomplete_aspects:
        sends.append(
            Send(
                "research",
                {
                    "aspect": aspect,  # StructuredAspect with name, reasoning, key_questions, completed
                    "dimension": dimension,
                    "topic": topic,
                    "research_config": research_config,
                    "reference_materials": reference_materials,
                    "research_context": research_context,
                    "research_session_id": research_session_id,  # Pass session ID
                    "user_id": user_id,  # Pass user_id for event tracking
                    "aspects_by_dimension": aspects_by_dimension  # Full structure for context
                }
            )
        )

    return sends






def continue_to_dimension_reduction(state: ResearchState) -> List[Send]:
    """
    Fan-out: Create parallel tasks for dimension document creation.

    Each dimension gets its own dimension_reduction_node execution.
    """
    dimensions = state.get("dimensions", [])
    topic = state.get("topic", "")
    aspects_by_dimension = state.get("aspects_by_dimension", {})
    research_by_aspect = state.get("research_by_aspect", {})
    research_context = state.get("research_context", "")

    print(f"\n{'='*80}")
    print(f"STAGE 4: DIMENSION REDUCTION (Word Document Creation)")
    print(f"{'='*80}")

    # Debug: Check state
    print(f"\n🔍 State Debug:")
    print(f"   dimensions from state: {dimensions}")
    print(f"   aspects_by_dimension keys: {list(aspects_by_dimension.keys()) if aspects_by_dimension else 'None'}")
    print(f"   research_by_aspect keys: {list(research_by_aspect.keys())[:5] if research_by_aspect else 'None'}")

    print(f"\n📤 Fanning out to {len(dimensions)} parallel document writers...")

    # Create parallel tasks for each dimension
    sends = []
    for dimension in dimensions:
        sends.append(
            Send(
                "dimension_reduction",
                {
                    "dimension": dimension,
                    "topic": topic,
                    "aspects_by_dimension": aspects_by_dimension,
                    "research_by_aspect": research_by_aspect,
                    "research_context": research_context,
                    "research_config": state.get("research_config", {})  # Pass model selection
                }
            )
        )

    return sends


def finalize_workflow(state: ResearchState) -> dict:
    """
    Finalize workflow: Upload outputs to S3, log completion, and save to AgentCore Memory.
    """
    from src.utils.workspace import get_workspace
    from src.utils.session_logger import get_session_logger
    from src.utils.s3_uploader import upload_research_outputs
    from src.utils.status_updater import get_status_updater
    from src.config.memory_config import get_memory_id_from_config, get_region, is_agentcore_enabled

    print(f"\n{'='*80}")
    print(f"WORKFLOW FINALIZATION")
    print(f"{'='*80}")

    dimensions = state.get("dimensions", [])
    aspects_by_dimension = state.get("aspects_by_dimension", {})
    report_file = state.get("report_file", "")
    report_pdf_file = state.get("report_pdf_file", "")
    draft_report_file = state.get("draft_report_file", "")
    dimension_documents = state.get("dimension_documents", {})
    research_session_id = state.get("research_session_id", "N/A")

    elapsed = time.time() - state.get("workflow_start_time", time.time())

    # Get status updater and update stage
    status_updater = get_status_updater(research_session_id)
    if status_updater:
        status_updater.update_stage('finalize')

    # Upload final report to S3
    # Note: Charts are already uploaded by bring_and_insert_chart tool
    s3_uploads = {}
    if research_session_id != "N/A":
        try:
            print("\n📤 Uploading final report to S3...")
            s3_uploads = upload_research_outputs(
                session_id=research_session_id,
                markdown_path=draft_report_file,
                docx_path=report_file,
                pdf_path=report_pdf_file,
                version='draft'  # Initial version is always 'draft'
            )
            print("   ✅ S3 uploads complete")
            print("   ℹ️  Charts were already uploaded by chart generation tool")

            # Save version info to Status table
            if status_updater and 'uploads' in s3_uploads:
                markdown_s3_key = s3_uploads['uploads'].get('markdown', {}).get('s3_key')
                docx_s3_key = s3_uploads['uploads'].get('docx', {}).get('s3_key')
                pdf_s3_key = s3_uploads['uploads'].get('pdf', {}).get('s3_key')

                if markdown_s3_key:
                    status_updater.create_version(
                        version_name='draft',
                        markdown_s3_key=markdown_s3_key,
                        docx_s3_key=docx_s3_key,
                        pdf_s3_key=pdf_s3_key,
                        created_by='system',
                        edit_type='initial'
                    )
                    status_updater.set_current_version('draft')
                    print("   ✅ Version 'draft' saved to Status table")
        except Exception as e:
            print(f"   ⚠️  S3 upload failed: {e}")
            s3_uploads = {'error': str(e)}

    # Check for various workflow errors
    errors = []

    # Check dimension_reduction errors
    if dimension_documents:
        failed_dimensions = [
            dim for dim, doc in dimension_documents.items() if doc is None
        ]
        if failed_dimensions:
            errors.append(f"Dimension reduction failed for: {', '.join(failed_dimensions)}")

    # Check report_writing error
    if not report_file:
        errors.append("Report writing/conversion failed")

    # Note: chart_generation errors are not critical (charts are optional)

    has_errors = len(errors) > 0

    # Update DynamoDB status - failed if any errors, otherwise completed
    if status_updater:
        # Update stage to workflow_complete to mark finalize as completed in UI
        status_updater.update_stage('workflow_complete')

        if has_errors:
            # Mark as failed due to workflow errors
            status_updater.update(
                status='failed',
                error='; '.join(errors),
                completed_at=datetime.now().isoformat()
            )
        else:
            # Mark as completed
            status_updater.mark_completed(
                report_file=report_file,
                report_pdf_file=report_pdf_file,
                dimension_documents=dimension_documents,
                s3_uploads=s3_uploads,
                elapsed_time=elapsed
            )

    # Log session completion
    if research_session_id != "N/A":
        session_logger = get_session_logger()
        session_logger.log_session_complete(
            session_id=research_session_id,
            dimensions=dimensions,
            aspects_by_dimension=aspects_by_dimension,
            report_file=report_file,
            elapsed_time=elapsed,
            s3_uploads=s3_uploads
        )

    # Log research complete event to AgentCore Memory
    if research_session_id != "N/A":
        from src.utils.event_tracker import get_event_tracker
        user_id = state.get("user_id")
        if not user_id:
            logger.warning("⚠️  user_id not found in state - event tracking skipped")

        event_tracker = get_event_tracker()
        if event_tracker and user_id:
            output_files = {
                'docx': report_file,
                'markdown': draft_report_file,
                'pdf': report_pdf_file
            }
            total_aspects = sum(len(aspects) for aspects in aspects_by_dimension.values())
            event_tracker.log_research_complete(
                session_id=research_session_id,
                dimensions=dimensions,
                total_aspects=total_aspects,
                elapsed_time=elapsed,
                output_files=output_files,
                s3_uploads=s3_uploads,
                actor_id=user_id
            )

    print(f"\n{'='*80}")
    print(f"WORKFLOW COMPLETE")
    print(f"{'='*80}")
    print(f"\n✅ Total workflow time: {elapsed:.2f}s")
    print(f"\n🔑 Research Session ID: {research_session_id}")
    print(f"\n📊 Final Summary:")
    print(f"   - Dimensions: {len(dimensions)}")
    print(f"   - Total Aspects: {sum(len(aspects) for aspects in aspects_by_dimension.values())}")
    print(f"   - Report File: {report_file}")

    # S3 summary
    if s3_uploads.get('uploads'):
        print(f"\n☁️  S3 Uploads:")
        if 'docx' in s3_uploads['uploads']:
            docx_info = s3_uploads['uploads']['docx']
            if 's3_uri' in docx_info:
                print(f"   - Word Document: {docx_info['s3_uri']}")
        if 'markdown' in s3_uploads['uploads']:
            md_info = s3_uploads['uploads']['markdown']
            if 's3_uri' in md_info:
                print(f"   - Markdown: {md_info['s3_uri']}")
        if 'pdf' in s3_uploads['uploads']:
            pdf_info = s3_uploads['uploads']['pdf']
            if 's3_uri' in pdf_info:
                print(f"   - PDF Document: {pdf_info['s3_uri']}")
        print(f"   ℹ️  Charts uploaded during chart generation phase")

    # Workspace summary
    workspace = get_workspace()
    workspace_info = workspace.get_info()
    print(f"\n📁 Local Workspace:")
    print(f"   - Location: {workspace_info['base_path']}")
    print(f"   - Dimension Documents: {workspace_info['dimension_documents']}")
    print(f"   - Final Reports: {workspace_info['final_reports']}")

    return {
        "current_stage": "workflow_complete",
        "s3_uploads": s3_uploads
    }


def create_workflow() -> StateGraph:
    """
    Create the unified dimensional research workflow.

    Flow:
    1. START → [topic_analysis + reference_preparation (if provided)] (parallel)
    2. topic_analysis → aspect_analysis (parallel by dimension)
    3. [reference_preparation + aspect_analysis] → aspect_preparation_barrier
    4. aspect_preparation_barrier → research_planning (unified refinement, runs once)
    5. research_planning → research (parallel by aspect)
    6. research → research_barrier
    7. research_barrier → dimension_reduction (parallel by dimension) - Creates markdown docs
    8. dimension_reduction → report_writing (barrier, merge + edit + summary → final markdown)
    9. report_writing → chart_generation (generate and insert charts into markdown)
    10. chart_generation → document_conversion (convert markdown to Word + PDF)
    11. document_conversion → finalize → END

    Returns:
        Compiled LangGraph workflow
    """
    # Clear any previous research results and documents
    from src.tools.research_submission_tool import clear_submitted_results
    from src.tools.word_document_tools import clear_active_documents
    from src.utils.workspace import get_workspace

    clear_submitted_results()
    clear_active_documents()

    # Initialize workspace and clean dimension documents from previous runs
    workspace = get_workspace()
    workspace.clean_dimensions()
    workspace.clean_temp()

    print(f"📁 Workspace initialized: {workspace.base_path}")
    print(f"   - ArXiv papers: {workspace.arxiv_dir}")
    print(f"   - Dimension docs: {workspace.dimensions_dir}")
    print(f"   - Final reports: {workspace.final_dir}")

    # Build workflow graph
    workflow = StateGraph(ResearchState)

    # Prepare nodes for map-reduce pattern
    def prepare_research(state: ResearchState):
        """Aggregator node - waits for all aspect_analysis to complete

        Note: reference_preparation now runs sequentially before topic_analysis,
        so reference results are already in state by the time we reach here.
        """
        from src.utils.status_updater import get_status_updater

        print(f"\n{'='*80}")
        print(f"PREPARE_RESEARCH - Aggregating all aspect_analysis results")
        print(f"{'='*80}")

        # NOTE: Do NOT flush dimensions here - they will be flushed after research_planning
        # with refined dimensions/aspects
        research_session_id = state.get("research_session_id")
        status_updater = get_status_updater(research_session_id)
        if status_updater:
            status_updater.update_stage('prepare_research')

        return {}

    def prepare_dimension_reduction(state: ResearchState):
        """Single node to trigger dimension_reduction fan-out after all research complete"""
        from src.utils.status_updater import get_status_updater

        print(f"\n{'='*80}")
        print(f"ALL RESEARCH COMPLETE - Preparing dimension reduction")
        print(f"{'='*80}")

        # Flush research results to DynamoDB (for UI display)
        research_session_id = state.get("research_session_id")
        status_updater = get_status_updater(research_session_id)
        if status_updater:
            # Flush accumulated research results
            research_by_aspect = state.get("research_by_aspect", {})
            for aspect_key, research_data in research_by_aspect.items():
                # Parse dimension and aspect from key
                parts = aspect_key.split("::")
                if len(parts) == 2:
                    dimension, aspect_name = parts
                    status_updater.add_research_result(dimension, aspect_name, research_data)

            status_updater.flush_research_results()
            status_updater.update_stage('prepare_dimension_reduction')

        return {}

    async def aggregate_dimensions(state: ResearchState):
        """Aggregator node: waits for all dimension_reduction to complete, then triggers report_writing"""
        from src.utils.status_updater import get_status_updater

        print(f"\n{'='*80}")
        print(f"ALL DIMENSION DOCUMENTS COMPLETE - Preparing report writing")
        print(f"{'='*80}")

        dimension_documents = state.get("dimension_documents", {})
        print(f"   Collected {len(dimension_documents)} dimension documents")
        print(f"   Documents: {list(dimension_documents.keys())}")

        research_session_id = state.get("research_session_id")
        status_updater = get_status_updater(research_session_id)
        if status_updater:
            status_updater.update_stage('aggregate_dimensions')

        return {}

    # Add nodes
    workflow.add_node("initialize_session", initialize_session)
    workflow.add_node("reference_preparation", reference_preparation_node)
    workflow.add_node("topic_analysis", topic_analysis_node)
    workflow.add_node("aspect_analysis", aspect_analysis_node)
    workflow.add_node("prepare_research", prepare_research, defer=True)  # Aggregator - waits for all incoming
    workflow.add_node("research_planning", research_planning_node)  # Real
    workflow.add_node("research", research_agent_node)
    workflow.add_node("prepare_dimension_reduction", prepare_dimension_reduction, defer=True)  # Wait for all research
    workflow.add_node("dimension_reduction", dimension_reduction_node)
    workflow.add_node("aggregate_dimensions", aggregate_dimensions, defer=True)  # Wait for all dimension_reduction
    workflow.add_node("report_writing", report_writing_node)  # Single execution after aggregation
    workflow.add_node("chart_generation", chart_generation_node)  # Single execution after report_writing, insert charts into markdown
    workflow.add_node("document_conversion", document_conversion_node)  # Single execution after chart_generation, convert to Word/PDF
    workflow.add_node("finalize", finalize_workflow)

    # START → initialize_session (generates session_id and updates state)
    workflow.add_edge(START, "initialize_session")

    # initialize_session → conditional: reference_preparation (if references exist) or topic_analysis (skip if no references)
    workflow.add_conditional_edges(
        "initialize_session",
        route_from_start,
        ["reference_preparation", "topic_analysis"]
    )

    # reference_preparation → topic_analysis (sequential: references are processed before topic analysis)
    workflow.add_edge("reference_preparation", "topic_analysis")

    # topic_analysis → aspect_analysis (parallel fan-out from single point)
    workflow.add_conditional_edges(
        "topic_analysis",
        continue_to_aspect_analysis,
        ["aspect_analysis"]
    )

    # aspect_analysis → prepare_research (automatic fan-in with defer=True)
    workflow.add_edge("aspect_analysis", "prepare_research")

    # prepare_research → research_planning (single execution after all aspect_analysis complete)
    workflow.add_edge("prepare_research", "research_planning")

    # research_planning → research (map: parallel fan-out)
    workflow.add_conditional_edges(
        "research_planning",
        continue_to_research,
        ["research"]
    )

    # research → prepare_dimension_reduction (automatic fan-in)
    workflow.add_edge("research", "prepare_dimension_reduction")

    # prepare_dimension_reduction → dimension_reduction (map: parallel fan-out)
    workflow.add_conditional_edges(
        "prepare_dimension_reduction",
        continue_to_dimension_reduction,
        ["dimension_reduction"]
    )

    # dimension_reduction → aggregate_dimensions (automatic fan-in with defer=True)
    workflow.add_edge("dimension_reduction", "aggregate_dimensions")

    # aggregate_dimensions → report_writing (single execution after all dimensions aggregated)
    workflow.add_edge("aggregate_dimensions", "report_writing")

    # report_writing → chart_generation (single execution, draft markdown ready)
    workflow.add_edge("report_writing", "chart_generation")

    # chart_generation → document_conversion (single execution, charts inserted into markdown)
    workflow.add_edge("chart_generation", "document_conversion")

    # document_conversion → finalize → END
    workflow.add_edge("document_conversion", "finalize")
    workflow.add_edge("finalize", END)

    # Compile workflow without checkpointer
    # We use custom ResearchEventTracker instead of LangGraph checkpointer for:
    # - High-level research event tracking (not low-level state snapshots)
    # - Searchable metadata and filtering
    # - Cost efficiency (fewer events than checkpoint-per-node)
    # Note: Concurrency control is handled by semaphores in individual nodes
    # See src/utils/concurrency.py and CONCURRENCY_LIMITS in research_config.py
    from src.utils.event_tracker import get_event_tracker

    # Initialize event tracker (singleton)
    event_tracker = get_event_tracker()
    if event_tracker:
        print(f"📝 Research event tracking enabled")
    else:
        print(f"📝 Research event tracking disabled")

    return workflow.compile()


# Example usage
if __name__ == "__main__":
    import uuid

    # Create workflow
    app = create_workflow()

    # Test with sample query
    test_session_id = f"test-session-{uuid.uuid4()}"

    config = {
        "configurable": {"thread_id": test_session_id},
        "run_name": "dimensional_research_run",
        "tags": ["dimensional-research", "test"]
    }

    # Simple test topic
    result = app.invoke(
        {
            "topic": "Recent advances in transformer attention mechanisms",
            "workflow_start_time": time.time()
        },
        config=config
    )

    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)
    print(f"\nDimensions: {result.get('dimensions', [])}")
    print(f"\nAspects by Dimension:")
    for dim, aspects in result.get('aspects_by_dimension', {}).items():
        print(f"  {dim}: {len(aspects)} aspects")
