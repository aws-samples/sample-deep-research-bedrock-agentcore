# Model Configuration Guide

This guide explains how to configure, customize, and add AI models for the Dimensional Research Agent.

## Overview

The agent uses a centralized **model registry** (`shared/model_registry.json`) that defines:
- Available models and their Bedrock IDs
- Model metadata and recommendations
- Per-stage model combinations for research workflows

## Model Aliases

Shortcuts for commonly used models:

```json
"aliases": {
  "claude_haiku": "claude_haiku45",
  "claude_sonnet": "claude_sonnet45",
  "haiku45": "claude_haiku45",
  "sonnet45": "claude_sonnet45"
}
```

Use aliases in configuration for easier reference.

## Adding New Models

Edit `shared/model_registry.json`:

```json
{
  "models": {
    "your_model_id": {
      "id": "your_model_id",
      "label": "Your Model Name",
      "description": "Brief description of capabilities",
      "bedrock_id": "your.bedrock.model-id-v1:0",
      "provider": "provider_name",
      "category": "general|premium|fast|specialized",
      "recommended_for": ["chat", "research"]
    }
  }
}
```

### Code Reference

Model loading: `research-agent/src/utils/model_utils.py`
Registry loading: `research-agent/src/config/models.py`

## Frontend Model Selector

The UI displays available models from the registry:

**Location:** `frontend/src/components/research/CreateResearch.jsx`

**Model Selection:**
```javascript
<FormField label="Model">
  <Select
    selectedOption={selectedModel}
    onChange={({ detail }) => setSelectedModel(detail.selectedOption)}
    options={[
      { label: "Amazon Nova Pro", value: "nova_pro" },
      { label: "Claude Sonnet 4.5", value: "claude_sonnet45" },
      { label: "Claude Haiku 4.5", value: "claude_haiku45" },
      { label: "Qwen3", value: "qwen3_mixed" },
      { label: "Llama Maverick", value: "llama_maverick" }
    ]}
  />
</FormField>
```

---

For more information:
- [RESEARCH_METHODOLOGY.md](./RESEARCH_METHODOLOGY.md) - Workflow details
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [README.md](./README.md) - Quick start
