"""Cancellation utilities for research workflow

Provides utilities to check for research cancellation and stop execution gracefully.
"""


class ResearchCancelledException(Exception):
    """Raised when research is cancelled by user"""
    pass


def check_cancellation(state: dict) -> None:
    """
    Check if research has been cancelled by user.

    Call this at the start of each workflow node to enable graceful cancellation.

    Args:
        state: Workflow state containing research_session_id

    Raises:
        ResearchCancelledException: If research is cancelled

    Example:
        @traceable(name="my_node")
        def my_node(state: ResearchState) -> Dict[str, Any]:
            check_cancellation(state)  # Check at node start

            # ... node logic ...

            return {"result": data}
    """
    from src.utils.status_updater import get_status_updater

    research_session_id = state.get("research_session_id")

    if not research_session_id:
        return  # No session ID, can't check

    status_updater = get_status_updater(research_session_id)

    if not status_updater:
        return  # Status updater not available

    current_status = status_updater.get_status()

    if current_status and current_status.get('status') in ['cancelling', 'cancelled']:
        print(f"🛑 Research cancellation detected - stopping node")
        raise ResearchCancelledException("Research cancelled by user")
