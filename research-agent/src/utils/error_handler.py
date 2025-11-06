"""Error handling utilities for workflow nodes

Provides graceful error handling for parallel nodes to prevent workflow failures.
Errors are logged, tracked, and reported without stopping the workflow.
"""

import traceback
from typing import Dict, Any, Callable
from functools import wraps


def get_user_friendly_error_message(error: Exception, node_name: str, context: Dict[str, Any] = None) -> str:
    """
    Convert technical error messages to user-friendly explanations.

    Args:
        error: The exception that occurred
        node_name: Name of the node where error occurred
        context: Context information (dimension, aspect, etc.)

    Returns:
        User-friendly error message
    """
    error_msg = str(error).lower()
    error_type = type(error).__name__

    # Check for RecursionError first (critical error type)
    if error_type == "RecursionError" or "recursion" in error_msg:
        return "Agent exceeded maximum iterations - research task too complex or requires more steps than allowed"

    # Simple error categorization
    if "timeout" in error_msg or "timed out" in error_msg:
        return "Request timeout - service took too long to respond"

    if "rate limit" in error_msg or "throttl" in error_msg:
        return "Rate limit exceeded - too many requests"

    if "connection" in error_msg or "network" in error_msg:
        return "Network connection error"

    if "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg:
        return "Authentication failed - invalid API key"

    if "404" in error_msg or "not found" in error_msg:
        return "Resource not found"

    if "model" in error_msg or "bedrock" in error_msg:
        return "AI model error - try different model"

    if "token" in error_msg or "context length" in error_msg:
        return "Input too long for model"

    if "validation" in error_msg or "parse" in error_msg:
        return "Invalid response format from AI"

    if "memory" in error_msg:
        return "Out of memory"

    # Default: show error type + first 80 chars of message
    return f"{error_type}: {str(error)[:80]}"


def handle_node_error(node_name: str, fallback_return: Dict[str, Any] = None, extract_context: Callable = None):
    """
    Decorator for workflow nodes to handle errors gracefully.

    Errors are:
    - Logged to console with full traceback
    - Tracked per aspect/dimension for UI display
    - Returned in a structured format

    Args:
        node_name: Name of the node (for logging)
        fallback_return: Default return value on error (if None, returns empty dict)
        extract_context: Optional function to extract aspect/dimension from state

    Usage:
        @handle_node_error("aspect_analysis", extract_context=lambda s: {"dimension": s.get("dimension")})
        def aspect_analysis_node(state):
            # ... node logic
    """
    if fallback_return is None:
        fallback_return = {}

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                trace = traceback.format_exc()

                # Extract state and context
                state = args[0] if args and isinstance(args[0], dict) else kwargs.get('state')
                context = {}

                if state:
                    # Extract aspect/dimension info for better error reporting
                    if extract_context:
                        context = extract_context(state)
                    else:
                        # Auto-extract common fields
                        if "aspect" in state:
                            aspect = state["aspect"]
                            context["aspect"] = aspect.get("name") if isinstance(aspect, dict) else str(aspect)
                        if "dimension" in state:
                            context["dimension"] = state["dimension"]

                context_str = ""
                if context:
                    context_str = f" ({', '.join(f'{k}={v}' for k, v in context.items())})"

                print("\n" + "="*80)
                print(f"❌ ERROR in {node_name}{context_str}")
                print("="*80)
                print(f"Error: {error_msg}")
                print(f"\nFull traceback:")
                print(trace)
                print("="*80)
                print(f"⚠️  Continuing workflow with fallback value...")
                print("="*80 + "\n")

                # Update DynamoDB with error and context
                try:
                    if state:
                        from src.utils.status_updater import get_status_updater
                        session_id = state.get("research_session_id")
                        status_updater = get_status_updater(session_id)
                        if status_updater:
                            # Get user-friendly message
                            user_message = get_user_friendly_error_message(e, node_name, context)

                            status_updater.add_error(node_name, user_message, context)

                            # Mark specific aspect/dimension as failed
                            if node_name == "research_agent" and "aspect" in context and "dimension" in context:
                                status_updater.mark_research_failed(context["dimension"], context["aspect"], user_message)
                            elif node_name == "dimension_reduction" and "dimension" in context:
                                status_updater.mark_dimension_failed(context["dimension"], user_message)

                except Exception as update_error:
                    print(f"⚠️  Could not update error in DynamoDB: {update_error}")

                # Return fallback value to allow workflow to continue
                return fallback_return

        return wrapper
    return decorator


def safe_execute(func: Callable, *args, context: str = "operation", **kwargs) -> Any:
    """
    Execute a function safely with error handling.

    Logs errors but allows workflow to continue by returning None.

    Args:
        func: Function to execute
        *args: Function arguments
        context: Description of what's being executed (for logging)
        **kwargs: Function keyword arguments

    Returns:
        Function result or None on error

    Usage:
        result = safe_execute(llm.invoke, prompt, context="LLM call")
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_msg = str(e)
        trace = traceback.format_exc()

        print(f"\n⚠️  Error during {context}: {error_msg}")
        print(f"   Traceback:\n{trace}")
        print(f"   Continuing with None value...\n")

        return None


class ErrorAccumulator:
    """
    Accumulate errors during workflow execution.

    Thread-safe error collection for parallel nodes.
    Errors are stored and can be retrieved for reporting.
    """

    def __init__(self):
        import threading
        self._errors = []
        self._lock = threading.Lock()

    def add_error(self, node: str, error: str, details: Dict[str, Any] = None):
        """Add an error to the accumulator"""
        with self._lock:
            error_entry = {
                "node": node,
                "error": error,
                "timestamp": self._get_timestamp(),
            }
            if details:
                error_entry["details"] = details

            self._errors.append(error_entry)
            print(f"📝 Error recorded: {node} - {error[:100]}")

    def get_errors(self) -> list:
        """Get all accumulated errors"""
        with self._lock:
            return list(self._errors)

    def has_errors(self) -> bool:
        """Check if any errors were accumulated"""
        with self._lock:
            return len(self._errors) > 0

    def get_summary(self) -> str:
        """Get a formatted summary of all errors"""
        with self._lock:
            if not self._errors:
                return "No errors occurred during workflow execution."

            summary = f"\n{'='*80}\n"
            summary += f"⚠️  WORKFLOW ERRORS SUMMARY ({len(self._errors)} errors)\n"
            summary += f"{'='*80}\n\n"

            for i, error in enumerate(self._errors, 1):
                summary += f"{i}. [{error['node']}] at {error['timestamp']}\n"
                summary += f"   Error: {error['error']}\n"
                if 'details' in error:
                    summary += f"   Details: {error['details']}\n"
                summary += "\n"

            summary += f"{'='*80}\n"
            return summary

    def clear(self):
        """Clear all errors"""
        with self._lock:
            self._errors.clear()

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


# Global error accumulator for workflow
_workflow_error_accumulator = None


def get_error_accumulator() -> ErrorAccumulator:
    """Get or create global error accumulator"""
    global _workflow_error_accumulator
    if _workflow_error_accumulator is None:
        _workflow_error_accumulator = ErrorAccumulator()
    return _workflow_error_accumulator


def reset_error_accumulator():
    """Reset global error accumulator (call at workflow start)"""
    global _workflow_error_accumulator
    _workflow_error_accumulator = ErrorAccumulator()
