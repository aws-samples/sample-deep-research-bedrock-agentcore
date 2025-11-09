"""LLM configuration for dimensional research workflow

This module manages LLM model selection and configuration for different workflow stages.
Each node can use a different model based on its requirements:
- Structured output needs: Use models with strong JSON generation
- Agent capabilities: Use models with good tool use and reasoning
- Cost optimization: Use faster/cheaper models for simpler tasks

Models are configured via NODE_LLM_MAPPING and can be changed dynamically.
"""

import os
from typing import Dict, Any
from langchain_aws import ChatBedrockConverse


# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

# ============================================================================
# Available LLM Models
# ============================================================================
# Short name -> Full Bedrock model ID mapping
# Add new models here as they become available

LLM_MODELS = {
    # Anthropic Claude models (recommended for research tasks)
    "sonnet4": "us.anthropic.claude-sonnet-4-20250514-v1:0",  # Balanced performance
    "sonnet45": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Latest, best quality
    "haiku35": "anthropic.claude-3-5-haiku-20241022-v1:0",  # Fast, cost-effective (Haiku 3.5)
    "haiku45": "us.anthropic.claude-haiku-4-5-20251001-v1:0",  # Latest Haiku, faster and cheaper

    # Amazon Nova models
    "nova_pro": "us.amazon.nova-pro-v1:0",  # General purpose

    # Meta Llama models
    # NOTE: Llama Maverick has limitations with ReAct agents - fails to generate final synthesis
    "llama_maverick": "us.meta.llama4-maverick-17b-instruct-v1:0",  # ⚠️ Not recommended for research_agent
    "llama_scout": "us.meta.llama4-scout-17b-instruct-v1:0",  # Scout variant for better agent performance

    # Qwen models
    "qwen3_235b": "qwen.qwen3-235b-a22b-2507-v1:0",  # Qwen3 235B - High capability
    "qwen3_32b": "qwen.qwen3-32b-v1:0",  # Qwen3 32B - Fast and efficient
}

# ============================================================================
# Model Combination Presets
# ============================================================================
# Each preset defines which model to use for each workflow node
# This allows UI to provide simple options while backend uses optimal combinations

MODEL_COMBINATIONS = {
    "nova_pro": {
        # All stages use Nova Pro - fast and cost-effective
        "reference_prep": "nova_pro",
        "topic_analysis": "nova_pro",
        "aspect_analysis": "nova_pro",
        "research_planning": "nova_pro",
        "research_agent": "nova_pro",
        "dimension_reduction": "nova_pro",
        "report_writing": "nova_pro",
        "chart_generation": "nova_pro",
    },
    "claude_sonnet45": {
        # All stages use Sonnet 4.5 for optimal quality
        "reference_prep": "sonnet45",      # High quality summaries needed
        "topic_analysis": "sonnet45",      # Critical dimension identification
        "aspect_analysis": "sonnet45",     # Parallel execution
        "research_planning": "sonnet45",   # Better structured output reliability
        "research_agent": "sonnet45",      # Agent tool use capability
        "dimension_reduction": "sonnet45", # Pattern-based integration
        "report_writing": "sonnet45",      # Final document quality critical
        "chart_generation": "sonnet45",    # Chart agent with tools
    },
    "llama_maverick": {
        # Mix: Llama Maverick for most stages, but use Llama Scout for research_agent
        # (Llama Maverick fails to generate final synthesis in ReAct pattern)
        "reference_prep": "llama_maverick",
        "topic_analysis": "llama_maverick",
        "aspect_analysis": "llama_maverick",
        "research_planning": "llama_maverick",
        "research_agent": "llama_scout",  # Override: Use Scout for better ReAct agent performance
        "dimension_reduction": "llama_maverick",
        "report_writing": "llama_maverick",
        "chart_generation": "llama_maverick",
    },
    "claude_haiku45": {
        # All stages use Claude Haiku 4.5 - fastest and most cost-effective
        "reference_prep": "haiku45",
        "topic_analysis": "haiku45",
        "aspect_analysis": "haiku45",
        "research_planning": "haiku45",
        "research_agent": "haiku45",
        "dimension_reduction": "haiku45",
        "report_writing": "haiku45",
        "chart_generation": "haiku45",
    },
    "qwen3_mixed": {
        # Mix: Use Qwen3-235B for complex structured tasks, 32B for others
        "reference_prep": "qwen3_32b",
        "topic_analysis": "qwen3_235b",       # Needs structured output accuracy
        "aspect_analysis": "qwen3_32b",
        "research_planning": "qwen3_235b",    # Critical: must maintain exact dimension/aspect counts
        "research_agent": "qwen3_32b",
        "dimension_reduction": "qwen3_32b",
        "report_writing": "qwen3_32b",
        "chart_generation": "qwen3_32b",
    },
}

# Node-specific LLM assignments (will be set dynamically based on model combination)
NODE_LLM_MAPPING = MODEL_COMBINATIONS["claude_sonnet45"]  # Default to claude_sonnet45


# ============================================================================
# Default LLM Settings
# ============================================================================
DEFAULT_LLM_SETTINGS = {
    "temperature": 0.1,  # Low temperature for consistent, focused outputs
    "max_tokens": 8192,  # Maximum tokens per response (safe for all models)
}

# ============================================================================
# Prompt Caching Configuration
# ============================================================================
# Models that support prompt caching (for cost optimization)
# Caching is applied automatically in nodes that have long, repeated context
CACHING_SETTINGS = {
    "enable_prompt_caching": True,  # Set to False to disable caching globally
    "supported_models": [
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Sonnet 4.5
        "us.anthropic.claude-sonnet-4-20250514-v1:0",  # Sonnet 4
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",  # Haiku 4.5
        "us.amazon.nova-pro-v1:0",  # Nova Pro
        "anthropic.claude-3-5-haiku-20241022-v1:0",  # Haiku 3.5
    ]
}


def get_llm_for_node(node_name: str, state: dict = None, **kwargs) -> ChatBedrockConverse:
    """
    Get LLM instance for a specific workflow node.

    This function returns a configured LLM instance based on the node name.
    Each node can have a different model assignment via MODEL_COMBINATIONS.

    Args:
        node_name: Name of the workflow node (e.g., "research_agent", "topic_analysis")
        state: Optional workflow state containing research_config with llm_model
        **kwargs: Additional parameters to override defaults (temperature, max_tokens, etc.)

    Returns:
        ChatBedrockConverse: Configured LLM instance ready to use

    Example:
        >>> llm = get_llm_for_node("research_agent")
        >>> llm = get_llm_for_node("topic_analysis", state=state, temperature=0.2)
    """
    import boto3
    from botocore.config import Config

    # Determine which model combination to use
    model_combination = "claude_sonnet45"  # Default

    if state and isinstance(state, dict):
        research_config = state.get("research_config", {})
        if isinstance(research_config, dict):
            llm_model = research_config.get("llm_model", "claude_sonnet45")
            # Validate and use the model combination
            if llm_model in MODEL_COMBINATIONS:
                model_combination = llm_model

    # Get the model assignment for this node from the combination
    node_mapping = MODEL_COMBINATIONS.get(model_combination, MODEL_COMBINATIONS["claude_sonnet45"])
    model_type = node_mapping.get(node_name, "nova_pro")

    # Get the actual Bedrock model ID
    model_id = LLM_MODELS.get(model_type, LLM_MODELS["nova_pro"])

    # Merge default settings with any overrides
    settings = {**DEFAULT_LLM_SETTINGS, **kwargs}

    # Timeout configuration for Bedrock API calls
    # read_timeout: Time to receive FIRST response byte (not total generation time)
    # Once LLM starts responding, streaming continues regardless of timeout
    node_timeouts = {
        'dimension_reduction': 300,  # 5 minutes - increased for complex synthesis
        'report_writing': 300,       # 5 minutes - increased for document editing
        'research_agent': 180,       # 3 minutes
    }
    read_timeout = node_timeouts.get(node_name, 180)  # Default 3 minutes

    boto_config = Config(
        read_timeout=read_timeout,
        connect_timeout=10,
        retries={'max_attempts': 3, 'mode': 'standard'}  # Changed to standard for predictable retry
    )

    bedrock_client = boto3.client(
        'bedrock-runtime',
        region_name=AWS_REGION,
        config=boto_config
    )

    return ChatBedrockConverse(
        model=model_id,
        client=bedrock_client,
        **settings
    )


# ============================================================================
# Helper Functions
# ============================================================================

def get_base_model() -> ChatBedrockConverse:
    """
    Get base model for general purpose use.

    Returns default model used by topic_analysis node.
    Useful for one-off LLM calls outside the main workflow.
    """
    return get_llm_for_node("topic_analysis")


def get_model_id(model_type: str = "nova_pro") -> str:
    """
    Get full Bedrock model ID for a short model name.

    Args:
        model_type: Short model name (e.g., "sonnet4", "nova_pro")

    Returns:
        Full Bedrock model ID string

    Example:
        >>> get_model_id("sonnet4")
        'us.anthropic.claude-sonnet-4-20250514-v1:0'
    """
    return LLM_MODELS.get(model_type, LLM_MODELS["nova_pro"])


def get_model_id_for_node(node_name: str, state: dict = None) -> str:
    """
    Get Bedrock model ID string for a specific workflow node.

    Similar to get_llm_for_node() but returns only the model ID string
    instead of a configured LLM instance. Useful for direct boto3 API calls.

    Args:
        node_name: Name of the workflow node (e.g., "reference_prep", "topic_analysis")
        state: Optional workflow state containing research_config with llm_model

    Returns:
        str: Full Bedrock model ID

    Example:
        >>> model_id = get_model_id_for_node("reference_prep", state)
        'us.anthropic.claude-haiku-4-5-20251001-v1:0'
    """
    # Determine which model combination to use
    model_combination = "claude_sonnet45"  # Default

    if state and isinstance(state, dict):
        research_config = state.get("research_config", {})
        if isinstance(research_config, dict):
            llm_model = research_config.get("llm_model", "claude_sonnet45")
            # Validate and use the model combination
            if llm_model in MODEL_COMBINATIONS:
                model_combination = llm_model

    # Get the model assignment for this node from the combination
    node_mapping = MODEL_COMBINATIONS.get(model_combination, MODEL_COMBINATIONS["claude_sonnet45"])
    model_type = node_mapping.get(node_name, "nova_pro")

    # Get the actual Bedrock model ID
    model_id = LLM_MODELS.get(model_type, LLM_MODELS["nova_pro"])

    return model_id


def update_node_llm(node_name: str, model_type: str) -> None:
    """
    Dynamically update LLM assignment for a specific node.

    Useful for runtime model switching or experimentation.

    Args:
        node_name: Name of the workflow node
        model_type: Model type to assign (must exist in LLM_MODELS)

    Raises:
        ValueError: If model_type is not found in LLM_MODELS

    Example:
        >>> update_node_llm("research_agent", "sonnet45")
        ✅ Updated research_agent to use sonnet45 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)
    """
    if model_type in LLM_MODELS:
        NODE_LLM_MAPPING[node_name] = model_type
        print(f"✅ Updated {node_name} to use {model_type} ({LLM_MODELS[model_type]})")
    else:
        available = ", ".join(LLM_MODELS.keys())
        raise ValueError(f"Unknown model type: {model_type}. Available: {available}")


def get_current_config() -> Dict[str, Any]:
    """
    Get complete current LLM configuration.

    Returns a dictionary with all configuration details including:
    - Available models
    - Node-to-model assignments
    - Default settings
    - AWS region

    Returns:
        Dictionary containing complete configuration

    Example:
        >>> config = get_current_config()
        >>> print(config['node_assignments']['research_agent'])
        'sonnet4'
    """
    return {
        "models": LLM_MODELS,
        "node_assignments": NODE_LLM_MAPPING,
        "default_settings": DEFAULT_LLM_SETTINGS,
        "caching_settings": CACHING_SETTINGS,
        "region": AWS_REGION
    }
