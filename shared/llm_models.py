"""
Shared LLM Model ID mappings for all agents
This is the single source of truth for model configurations
"""

# Short name -> Full Bedrock model ID mapping
LLM_MODELS = {
    # Anthropic Claude models (recommended for research tasks)
    "claude_sonnet4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "claude_sonnet45": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "claude_haiku": "us.anthropic.claude-haiku-4-5-20251001-v1:0",  # Haiku 4.5 (latest)
    "claude_haiku35": "anthropic.claude-3-5-haiku-20241022-v1:0",
    "claude_haiku45": "us.anthropic.claude-haiku-4-5-20251001-v1:0",

    # Legacy short names (for backward compatibility with Research Agent)
    "sonnet4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "sonnet45": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "haiku35": "anthropic.claude-3-5-haiku-20241022-v1:0",
    "haiku45": "us.anthropic.claude-haiku-4-5-20251001-v1:0",

    # Amazon Nova models
    "nova_pro": "us.amazon.nova-pro-v1:0",

    # Meta Llama models
    "llama_maverick": "us.meta.llama4-maverick-17b-instruct-v1:0",
    "llama_scout": "us.meta.llama4-scout-17b-instruct-v1:0",

    # Qwen models
    "qwen3_235b": "qwen.qwen3-235b-a22b-2507-v1:0",
    "qwen3_32b": "qwen.qwen3-32b-v1:0",
    "qwen3_mixed": "qwen.qwen3-32b-v1:0",  # Alias for compatibility (Chat agent uses single model)
}

# Default model ID (full Bedrock model ID)
DEFAULT_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"  # Haiku 3.5
