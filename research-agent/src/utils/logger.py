"""Logging configuration for dimensional research agent

Provides structured logging that works with CloudWatch Logs and local development.
"""

import logging
import sys
from typing import Optional

# Global logger instance
_logger: Optional[logging.Logger] = None


def setup_logger(
    name: str = "research_agent",
    level: str = "INFO",
    format_string: Optional[str] = None
) -> logging.Logger:
    """Set up logger with CloudWatch-compatible configuration.

    This sets up the root logger or a base logger that all child loggers inherit from.

    Args:
        name: Logger name (use None or "" for root logger)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance
    """
    # Get root logger if name is empty, otherwise get named logger
    logger = logging.getLogger(name if name else None)

    # Only configure if not already configured
    if not logger.handlers:
        # Set level
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)

        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        # Create formatter
        if format_string is None:
            # CloudWatch-friendly format: timestamp, level, logger name, message
            format_string = '%(asctime)s [%(levelname)s] %(name)s - %(message)s'

        formatter = logging.Formatter(
            format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        # Add handler
        logger.addHandler(handler)

        # Don't prevent propagation - let child loggers inherit
        # Only set propagate=False for root logger
        if not name:
            logger.propagate = False

    return logger


def get_logger(name: str = "research_agent") -> logging.Logger:
    """Get or create logger instance.

    Args:
        name: Logger name (default: research_agent)

    Returns:
        Logger instance
    """
    global _logger

    if _logger is None:
        _logger = setup_logger(name)

    return _logger


# Convenience function to get module-specific logger
def get_module_logger(module_name: str) -> logging.Logger:
    """Get logger for specific module.

    Args:
        module_name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(f"research_agent.{module_name}")
