"""
Centralized Model Registry
Single source of truth for all LLM model configurations
"""
import json
import os
from typing import Dict, List, Optional

# Load model registry from JSON
_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), 'model_registry.json')

with open(_REGISTRY_PATH, 'r') as f:
    _REGISTRY = json.load(f)

# Extract models and aliases
MODELS = _REGISTRY['models']
ALIASES = _REGISTRY['aliases']
RESEARCH_COMBINATIONS = _REGISTRY['research_combinations']


def get_bedrock_id(model_id: str) -> str:
    """
    Get Bedrock model ID from short name

    Args:
        model_id: Short model ID (e.g., 'claude_haiku45' or alias like 'claude_haiku')

    Returns:
        Full Bedrock model ID (e.g., 'us.anthropic.claude-haiku-4-5-20251001-v1:0')
    """
    # Resolve alias
    resolved_id = ALIASES.get(model_id, model_id)

    # Get model
    model = MODELS.get(resolved_id)
    if not model:
        raise ValueError(f"Unknown model ID: {model_id}")

    return model['bedrock_id']


def get_model_info(model_id: str) -> Optional[Dict]:
    """Get full model information"""
    resolved_id = ALIASES.get(model_id, model_id)
    return MODELS.get(resolved_id)


def list_models(recommended_for: Optional[str] = None) -> List[Dict]:
    """
    List all available models

    Args:
        recommended_for: Filter by usage ('chat', 'research', or None for all)

    Returns:
        List of model info dicts
    """
    models = list(MODELS.values())

    if recommended_for:
        models = [m for m in models if recommended_for in m['recommended_for']]

    return models


# Legacy compatibility: LLM_MODELS dict
LLM_MODELS = {model_id: model['bedrock_id'] for model_id, model in MODELS.items()}

# Add aliases
for alias, target in ALIASES.items():
    if target in MODELS:
        LLM_MODELS[alias] = MODELS[target]['bedrock_id']

# Default model
DEFAULT_MODEL_ID = MODELS['claude_haiku45']['bedrock_id']


if __name__ == "__main__":
    # Test
    print("=== Available Models ===")
    for model in list_models():
        print(f"{model['id']}: {model['label']} ({model['bedrock_id']})")

    print("\n=== Test Bedrock ID Resolution ===")
    print(f"claude_haiku -> {get_bedrock_id('claude_haiku')}")
    print(f"claude_haiku45 -> {get_bedrock_id('claude_haiku45')}")
    print(f"nova_pro -> {get_bedrock_id('nova_pro')}")
