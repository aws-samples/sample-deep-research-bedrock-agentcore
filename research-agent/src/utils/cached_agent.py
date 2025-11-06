"""Cached ReAct Agent utility for token optimization

Provides a custom ReAct agent implementation that adds cache points to:
1. System prompts
2. Tool messages

This significantly reduces token usage in multi-turn agent conversations.
"""

from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt.tool_node import tools_condition
from langgraph.checkpoint.base import BaseCheckpointSaver


class CachedToolNode(ToolNode):
    """Custom ToolNode that adds cache points to tool messages.

    This enables prompt caching for tool results, dramatically reducing
    token usage when tools return large amounts of data.
    """

    def __call__(self, state):
        """Execute tools and add cache points to results."""
        # Call parent ToolNode to execute tools
        result = super().__call__(state)

        # Add cache points to tool messages
        if "messages" in result:
            cached_messages = []
            for msg in result["messages"]:
                if isinstance(msg, ToolMessage):
                    # Convert tool message content to cached format
                    cached_msg = ToolMessage(
                        content=[
                            {
                                "text": msg.content if isinstance(msg.content, str) else str(msg.content)
                            },
                            {"cachePoint": {"type": "default"}}
                        ],
                        tool_call_id=msg.tool_call_id,
                        name=msg.name
                    )
                    cached_messages.append(cached_msg)
                else:
                    cached_messages.append(msg)
            result["messages"] = cached_messages

        return result


def create_cached_react_agent(
    llm: BaseChatModel,
    tools: List[BaseTool],
    system_prompt: str,
    checkpointer: Optional[BaseCheckpointSaver] = None
):
    """Create a ReAct agent with prompt caching enabled.

    This creates a custom LangGraph workflow that:
    1. Caches the system prompt
    2. Caches tool message results
    3. Uses ReAct pattern (Reason + Act loop)

    Args:
        llm: Language model to use
        tools: List of tools available to the agent
        system_prompt: System prompt with instructions
        checkpointer: Optional checkpointer for conversation memory

    Returns:
        Compiled LangGraph agent with caching enabled

    Example:
        >>> agent = create_cached_react_agent(
        ...     llm=llm,
        ...     tools=[search_tool, calculator_tool],
        ...     system_prompt="You are a helpful assistant...",
        ...     checkpointer=MemorySaver()
        ... )
        >>> result = agent.invoke(
        ...     {"messages": [("user", "Search for AI news")]},
        ...     config={"configurable": {"thread_id": "123"}}
        ... )
    """
    # Create system message with cache point
    cached_system_message = SystemMessage(
        content=[
            {"text": system_prompt},
            {"cachePoint": {"type": "default"}}
        ]
    )

    # Create prompt template with cached system message
    custom_prompt = ChatPromptTemplate.from_messages([
        cached_system_message,
        MessagesPlaceholder(variable_name="messages"),
    ])

    # Bind tools to LLM
    model_with_tools = llm.bind_tools(tools)

    # Define agent node
    def call_model(state: MessagesState):
        """Agent reasoning step - calls LLM with tools."""
        messages = custom_prompt.invoke({"messages": state["messages"]})
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}

    # Build graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", CachedToolNode(tools))

    # Define edges: START → agent → tools (if needed) → agent → ...
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    # Compile with optional checkpointer
    return workflow.compile(checkpointer=checkpointer)


def supports_prompt_caching(llm: BaseChatModel) -> bool:
    """Check if the model supports prompt caching.

    Currently supports:
    - Claude Sonnet 4.5 (Bedrock)
    - Claude Sonnet 4 (Bedrock)
    - Amazon Nova Pro
    - Claude 3.5 Haiku (Bedrock)

    Args:
        llm: Language model to check

    Returns:
        True if caching is supported, False otherwise
    """
    model_name = getattr(llm, 'model_id', getattr(llm, 'model', ''))

    supported_models = [
        'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        'us.anthropic.claude-sonnet-4-20250514-v1:0',
        'us.amazon.nova-pro-v1:0',
        'anthropic.claude-3-5-haiku-20241022-v1:0'
    ]

    return any(model in model_name for model in supported_models)
