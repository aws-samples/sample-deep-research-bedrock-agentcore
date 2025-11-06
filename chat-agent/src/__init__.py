"""
Chat Agent for Research Q&A
Uses Strands Agent with AgentCore Memory STM for conversation continuity
"""

from .agent import create_chat_agent, handle_chat_message

__all__ = ["create_chat_agent", "handle_chat_message"]
