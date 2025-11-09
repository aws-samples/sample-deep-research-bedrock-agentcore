# Configuration Management Guide

## Overview

The Research Gateway infrastructure uses a hybrid configuration management approach:

- **AWS Parameter Store**: Non-sensitive configuration values (table names, bucket names, URLs, Memory IDs)
- **AWS Secrets Manager**: Sensitive data (API keys, credentials)
- **Local .env**: Development environment configuration (fallback for all values)

This approach eliminates the need for `.bedrock_agentcore.yaml` and consolidates all local configuration in `.env`.

---

## Configuration Storage

### 1. Parameter Store (Non-Sensitive Config)

Stored in AWS Systems Manager Parameter Store with the following structure:

```
/research-gateway/{suffix}/agentcore/memory-id
/research-gateway/{suffix}/dynamodb/status-table
/research-gateway/{suffix}/s3/outputs-bucket
/research-gateway/{suffix}/config/region
/research-gateway/{suffix}/gateway/url
/research-gateway/{suffix}/langchain/project
/research-gateway/{suffix}/langchain/tracing-v2
```

**Values Stored:**
- `AGENTCORE_MEMORY_ID` - AgentCore Memory ID from parent deployment
- `DYNAMODB_STATUS_TABLE` - DynamoDB table name for status tracking
- `S3_OUTPUTS_BUCKET` - S3 bucket name for research outputs
- `AWS_REGION` - AWS region
- `GATEWAY_URL` - AgentCore Gateway URL
- `LANGCHAIN_PROJECT` - LangSmith project name (optional)
- `LANGCHAIN_TRACING_V2` - Enable LangSmith tracing (optional)

### 2. Secrets Manager (Sensitive Data)

Stored in AWS Secrets Manager with resource-specific names:

```
research-gateway-tavily-api-key-{suffix}
research-gateway-google-credentials-{suffix}
research-gateway-langchain-api-key-{suffix}  (optional)
```

**Values Stored:**
- `TAVILY_API_KEY` - Tavily AI Search API key (required)
- `GOOGLE_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` - Google Custom Search credentials (optional)
- `LANGCHAIN_API_KEY` - LangSmith API key for tracing (optional)

### 3. Local .env (Development)

For local development, all values can be kept in `.env`:

```bash
# AWS Configuration
AWS_REGION=us-west-2

# AWS Resources (from parent Terraform)
DYNAMODB_STATUS_TABLE=deep-research-agent-status-xxxxx
S3_OUTPUTS_BUCKET=deep-research-agent-outputs-xxxxx
AGENTCORE_MEMORY_ID=deep_research_memory_xxxxx

# LangSmith Configuration (Optional)
LANGCHAIN_API_KEY=lsv2_pt_xxxxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=research-agent

# API Keys
TAVILY_API_KEY=tvly-xxxxx
GOOGLE_API_KEY=AIzaSyAxxxxx
GOOGLE_SEARCH_ENGINE_ID=xxxxx
```

---

## Deployment Process

### 1. Prepare Environment

Ensure your `.env` file contains all required values:

```bash
cd /path/to/sample-deep-research-bedrock-agentcore
cat .env
```

Required values:
- `AGENTCORE_MEMORY_ID` (from parent Terraform)
- `DYNAMODB_STATUS_TABLE` (from parent Terraform)
- `S3_OUTPUTS_BUCKET` (from parent Terraform)
- `TAVILY_API_KEY` (your Tavily API key)

Optional values:
- `GOOGLE_API_KEY` (Google Custom Search)
- `GOOGLE_SEARCH_ENGINE_ID` (Google Custom Search)
- `LANGCHAIN_API_KEY` (LangSmith tracing)

### 2. Deploy Gateway Infrastructure

The deployment script automatically:
1. Loads `.env` file
2. Validates all required configuration
3. Stores values in Parameter Store and Secrets Manager
4. Deploys Lambda functions and Gateway

```bash
cd research-gateway-lambdas
./scripts/deploy.sh
```

### 3. Verify Deployment

After deployment, verify Parameter Store values:

```bash
# List all parameters
aws ssm describe-parameters \
  --parameter-filters "Key=Name,Option=BeginsWith,Values=/research-gateway/"

# Get specific parameter
aws ssm get-parameter \
  --name "/research-gateway/{suffix}/agentcore/memory-id" \
  --with-decryption
```

Verify Secrets Manager values:

```bash
# List all secrets
aws secretsmanager list-secrets \
  --filters Key=name,Values=research-gateway

# Get specific secret
aws secretsmanager get-secret-value \
  --secret-id research-gateway-tavily-api-key-{suffix}
```

---

## Agent Runtime Usage

### Python Configuration Loader

Use the provided configuration loader utility:

```python
from src.utils.config_loader import load_config, get_config

# Load all configuration
config = load_config()

# Access values
memory_id = config['AGENTCORE_MEMORY_ID']
dynamodb_table = config['DYNAMODB_STATUS_TABLE']
tavily_key = config['TAVILY_API_KEY']

# Or use helper function
memory_id = get_config('AGENTCORE_MEMORY_ID')
```

### Configuration Priority

The loader uses the following priority:

1. **AWS Services** (if available)
   - Parameter Store for config
   - Secrets Manager for secrets

2. **Local .env** (fallback)
   - Used if AWS services unavailable
   - Used for local development

### Force Local Development

To use only `.env` without AWS services:

```python
from src.utils.config_loader import load_config

# Disable AWS loading
config = load_config(use_aws=False)
```

---

## Migration from .bedrock_agentcore.yaml

### Old Approach

Previously, AgentCore Memory ID was stored in `.bedrock_agentcore.yaml`:

```yaml
default_agent: research_agent

agents:
  research_agent:
    memory:
      memory_id: YOUR_MEMORY_ID_HERE
      region: us-west-2
```

### New Approach

**For Production**: Terraform stores Memory ID in Parameter Store automatically.

**For Local Development**: Store Memory ID in `.env`:

```bash
AGENTCORE_MEMORY_ID=deep_research_memory_xxxxx
```

### Benefits

1. **Single Source of Truth**: All configuration in `.env` for local dev
2. **AWS Integration**: Automatic storage in Parameter Store/Secrets Manager
3. **No Manual Config Files**: No need to maintain `.bedrock_agentcore.yaml`
4. **Consistent Access**: Same config loader works for both local and AWS

---

## Terraform Variables

The Terraform deployment requires these variables:

```hcl
# Configuration values to be stored in Parameter Store
variable "agentcore_memory_id" {}
variable "dynamodb_status_table" {}
variable "s3_outputs_bucket" {}

# API keys to be stored in Secrets Manager
variable "tavily_api_key" {}
variable "google_api_key" {}          # optional
variable "google_search_engine_id" {} # optional

# Optional: LangSmith configuration
variable "langchain_api_key" {}       # optional
variable "langchain_project" {}       # optional
variable "langchain_tracing_v2" {}    # optional
```

These are automatically passed from `.env` by the deployment script.

---

## Troubleshooting

### Parameter Store Issues

**Problem**: Agent can't find Parameter Store values

**Solution**:
1. Verify parameters exist:
   ```bash
   aws ssm describe-parameters \
     --parameter-filters "Key=Name,Option=BeginsWith,Values=/research-gateway/"
   ```

2. Check IAM permissions for agent role:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "ssm:GetParameter",
       "ssm:GetParameters"
     ],
     "Resource": "arn:aws:ssm:*:*:parameter/research-gateway/*"
   }
   ```

3. Fall back to `.env` for local development:
   ```python
   config = load_config(use_aws=False)
   ```

### Secrets Manager Issues

**Problem**: Agent can't access secrets

**Solution**:
1. Verify secrets exist:
   ```bash
   aws secretsmanager list-secrets \
     --filters Key=name,Values=research-gateway
   ```

2. Check IAM permissions:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "secretsmanager:GetSecretValue"
     ],
     "Resource": "arn:aws:secretsmanager:*:*:secret:research-gateway-*"
   }
   ```

### Local Development Issues

**Problem**: Values not loading from `.env`

**Solution**:
1. Verify `.env` file exists and contains required values
2. Use absolute path or ensure working directory is correct:
   ```python
   from pathlib import Path
   from dotenv import load_dotenv

   env_path = Path(__file__).parent.parent / '.env'
   load_dotenv(env_path)
   ```

---

## Best Practices

1. **Never commit `.env`** to version control
   - Add `.env` to `.gitignore`
   - Use `.env.example` as template

2. **Use Parameter Store for non-sensitive config**
   - Table names, bucket names, URLs, IDs
   - Values that need to be shared across services

3. **Use Secrets Manager for sensitive data**
   - API keys, passwords, credentials
   - Values that need rotation

4. **Keep .env for local development**
   - All values in one place
   - Easy to update and test
   - No need for multiple config files

5. **Validate configuration at startup**
   - Check for missing required values
   - Fail fast with clear error messages
   - Log what configuration source is being used

---

## Summary

| Configuration Type | Production | Development |
|-------------------|------------|-------------|
| AgentCore Memory ID | Parameter Store | .env |
| DynamoDB Table | Parameter Store | .env |
| S3 Bucket | Parameter Store | .env |
| Gateway URL | Parameter Store | .env |
| AWS Region | Parameter Store | .env |
| Tavily API Key | Secrets Manager | .env |
| Google API Key | Secrets Manager | .env |
| LangChain API Key | Secrets Manager | .env |

All configuration is **automatically stored during Terraform deployment** and **automatically loaded by the config loader** at runtime.

No manual configuration files needed!
