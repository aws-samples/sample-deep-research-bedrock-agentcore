"""State definitions for dimensional research workflow"""

from typing import Any, Dict, List, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import MessagesState
import operator


def merge_dicts(left: Dict, right: Dict) -> Dict:
    """Merge two dictionaries, with right taking precedence"""
    if not left:
        return right
    if not right:
        return left
    merged = {**left, **right}
    return merged


class ReferenceMaterial(TypedDict):
    """Single reference material with comprehensive summary"""
    type: str  # "url" or "pdf"
    source: str  # URL or PDF filename
    title: str
    summary: str  # LLM-generated comprehensive summary
    key_points: List[str]  # Main takeaways
    note: str  # Optional user note


class StructuredAspect(TypedDict):
    """Structured aspect with research guidance"""
    name: str  # Name of the aspect
    reasoning: str  # Why this aspect matters and what to focus on
    key_questions: List[str]  # Research questions to investigate
    completed: bool  # Whether this aspect is covered by reference materials


class ResearchState(MessagesState):
    """
    Main state for dimensional research workflow.

    Follows testflight pattern:
    - Inherits from MessagesState for message handling
    - Uses Annotated types with reducers for parallel execution results
    - All fields optional to support partial updates from nodes
    """

    # Input
    topic: Optional[str]
    research_config: Optional[Dict[str, Any]]  # Research tool configuration
    research_context: Optional[str]  # Optional user-provided research context

    # Session Management
    bff_session_id: Optional[str]  # Session ID from BFF (passed from agent.py)
    research_session_id: Optional[str]  # Unique session ID for AgentCore Memory (same as bff_session_id)
    user_id: Optional[str]  # User ID for event tracking and memory isolation

    # Stage 0: Reference Preparation outputs
    reference_materials: Optional[List[ReferenceMaterial]]  # Prepared reference summaries

    # Stage 1: Topic Analysis outputs
    dimensions: Optional[List[str]]
    search_results: Optional[List[Dict[str, Any]]]

    # Stage 2: Aspect Analysis outputs (parallel by dimension)
    # Use merge_dicts reducer to combine results from parallel executions
    original_aspects_by_dimension: Annotated[
        Optional[Dict[str, List[StructuredAspect]]],
        merge_dicts
    ]

    # Stage 2.5: Research Planning outputs (refined structure)
    # This REPLACES original_aspects_by_dimension for research execution
    aspects_by_dimension: Optional[Dict[str, List[StructuredAspect]]]
    refinement_changes: Optional[List[str]]  # List of changes made during refinement

    # Stage 3: Research outputs (parallel by aspect)
    # Use merge_dicts reducer to combine research from parallel executions
    research_by_aspect: Annotated[
        Optional[Dict[str, Dict[str, Any]]],  # aspect_key -> structured research result
        merge_dicts
    ]

    # Stage 4: Writer outputs
    dimension_documents: Annotated[
        Optional[Dict[str, str]],  # dimension -> document filename
        merge_dicts
    ]
    draft_report_file: Optional[str]  # Draft markdown file path (for editor tools)
    report_file: Optional[str]  # Final docx file path
    report_pdf_file: Optional[str]  # Final PDF file path
    chart_files: Optional[List[Dict[str, str]]]  # List of chart file metadata (path, title, type)

    # Workflow metadata
    workflow_start_time: Optional[float]

    # Error handling
    error: Optional[str]


class AspectAnalysisState(TypedDict):
    """
    State for individual aspect analysis node (parallel execution).

    This is a subset of ResearchState used for parallel fan-out.
    Each parallel execution receives only the data it needs.
    """
    dimension: str
    topic: str
    reference_materials: List[ReferenceMaterial]  # Reference context
    research_config: Dict[str, Any]  # Research configuration
    research_context: str  # Optional user-provided research context


class AspectResearchState(TypedDict):
    """
    State for individual aspect research node (parallel execution with ReAct agent).

    This is passed to each ReAct agent instance for deep research.
    """
    aspect: StructuredAspect  # Structured aspect with reasoning and questions
    dimension: str
    topic: str
    research_config: Dict[str, Any]  # Research tool configuration
    reference_materials: List[ReferenceMaterial]  # Reference materials for context
    research_context: str  # Optional user-provided research context
    aspects_by_dimension: Dict[str, List[StructuredAspect]]  # Full research structure for context
    research_session_id: str  # Research session ID for tracking
    user_id: Optional[str]  # User ID for event tracking
