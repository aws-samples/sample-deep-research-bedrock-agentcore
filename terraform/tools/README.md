# Research Gateway Lambdas

AWS Lambda functions for research tools, deployed behind AWS Bedrock AgentCore Gateway using MCP (Model Context Protocol).

**6 Lambda Functions | 14 Research Tools | 1 AgentCore Gateway**

## 📁 Structure

```
research-gateway-lambdas/
├── lambdas/                    # Lambda function source code
│   ├── tavily/                 # Tavily search + extract (2 tools)
│   ├── wikipedia/              # Wikipedia search + get_article (2 tools)
│   ├── duckduckgo/             # DuckDuckGo web + news (2 tools)
│   ├── google-search/          # Google web + image search (2 tools)
│   ├── arxiv/                  # ArXiv search + get_paper (2 tools)
│   └── finance/                # Yahoo Finance (4 tools)
├── scripts/
│   ├── deploy.sh               # Main deployment script
│   ├── build-all-lambdas.sh    # Build all Lambda packages
│   ├── test-gateway-client.py  # Comprehensive testing
│   └── test-gateway-simple.py  # Quick tool list test
├── terraform/
│   ├── main.tf                 # Provider and data sources
│   ├── gateway.tf              # Gateway + 14 targets
│   ├── lambda.tf               # 6 Lambda functions
│   ├── iam.tf                  # IAM roles and policies
│   ├── secrets.tf              # Secrets Manager
│   ├── parameter_store.tf      # Parameter Store configuration
│   ├── variables.tf            # Input variables
│   └── outputs.tf              # Output values
├── docs/
│   └── CONFIGURATION.md        # Configuration management guide
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

**Required Tools:**
- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0
- Python 3.13 (for building Lambda packages)
- jq (for JSON parsing in deployment scripts)

**Required Configuration (.env):**

```bash
# From parent Terraform deployment
AGENTCORE_MEMORY_ID=deep_research_memory_xxxxx-xxxxxxx
DYNAMODB_STATUS_TABLE=deep-research-agent-status-xxxxx
S3_OUTPUTS_BUCKET=deep-research-agent-outputs-xxxxx

# Required API Key
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx

# AWS Configuration
AWS_REGION=us-west-2
```

**Optional Configuration (.env):**

```bash
# Google Custom Search (optional - Google tools disabled if not set)
GOOGLE_API_KEY=AIzaSyAxxxxx
GOOGLE_SEARCH_ENGINE_ID=xxxxx

# LangSmith Tracing (optional - tracing disabled if not set, does NOT cause deployment failure)
LANGCHAIN_API_KEY=lsv2_pt_xxxxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=research-agent
```

### Deploy

```bash
# Ensure .env file exists in parent directory
cd /path/to/dimensional-research-agent
cat .env  # Verify required values

# Deploy everything
cd research-gateway-lambdas
./scripts/deploy.sh
```

This will:
1. ✅ Load configuration from `.env`
2. ✅ Validate required values
3. ✅ Build all Lambda packages (6 functions)
4. ✅ Deploy Gateway with 14 tool targets
5. ✅ Store configuration in Parameter Store and Secrets Manager
6. ✅ Output deployment results and configuration paths

### Test

Quick test (list tools only):
```bash
python scripts/test-gateway-simple.py
```

Comprehensive test (test all tools):
```bash
# Install test dependencies first
pip install fastmcp>=2.0.0

# Run comprehensive tests
python scripts/test-gateway-client.py
```

Manual Lambda test:
```bash
# Get function name
LAMBDA_NAME=$(cd terraform && terraform output -raw tavily_lambda_name)

# Invoke directly
aws lambda invoke \
  --function-name $LAMBDA_NAME \
  --payload '{"tool":"tavily_search","parameters":{"query":"AI"}}' \
  response.json

cat response.json | jq '.'
```

View logs:
```bash
aws logs tail /aws/lambda/research-gateway-tavily-xxxxx --follow
```

## 📊 Architecture

```
Agent Runtime (ECS/Fargate)
    ↓ AWS SigV4 (IAM Auth)
AgentCore Gateway (MCP Protocol)
    ├─ 14 Tool Targets
    │   ├─ tavily_search → Tavily Lambda
    │   ├─ tavily_extract → Tavily Lambda
    │   ├─ wikipedia_search → Wikipedia Lambda
    │   ├─ wikipedia_get_article → Wikipedia Lambda
    │   ├─ ddg_search → DuckDuckGo Lambda
    │   ├─ ddg_news → DuckDuckGo Lambda
    │   ├─ google_web_search → Google Search Lambda
    │   ├─ google_image_search → Google Search Lambda
    │   ├─ arxiv_search → ArXiv Lambda
    │   ├─ arxiv_get_paper → ArXiv Lambda
    │   ├─ stock_quote → Finance Lambda
    │   ├─ stock_history → Finance Lambda
    │   ├─ financial_news → Finance Lambda
    │   └─ stock_analysis → Finance Lambda
    ↓
6 Lambda Functions
    ├─ Tavily (2 tools)
    ├─ Wikipedia (2 tools)
    ├─ DuckDuckGo (2 tools)
    ├─ Google Search (2 tools)
    ├─ ArXiv (2 tools)
    └─ Finance (4 tools)
```

## 🛠️ Available Tools

### Tavily (2 tools)
- **tavily_search**: AI-powered web search, returns up to 5 high-quality results
- **tavily_extract**: Extract clean content from URLs, removes ads and boilerplate

### Wikipedia (2 tools)
- **wikipedia_search**: Search Wikipedia articles, returns up to 5 results with snippets
- **wikipedia_get_article**: Get full content of specific Wikipedia article

### DuckDuckGo (2 tools)
- **ddg_search**: Web search using DuckDuckGo, returns up to 5 results
- **ddg_news**: News search with time filters (day/week/month)

### Google Search (2 tools)
- **google_web_search**: Web search via Google Custom Search API
- **google_image_search**: Image search with accessibility verification

### ArXiv (2 tools)
- **arxiv_search**: Search scientific papers, returns title/authors/abstract
- **arxiv_get_paper**: Get full paper content, supports batch retrieval

### Finance (4 tools)
- **stock_quote**: Current stock quotes with price, volume, key metrics
- **stock_history**: Historical price data (OHLCV) over specified period
- **financial_news**: Latest financial news articles for stocks
- **stock_analysis**: Comprehensive analysis with valuation metrics

## 🔑 Resources Created

**Lambda Functions (6):**
- Tavily, Wikipedia, DuckDuckGo, Google Search, ArXiv, Finance

**AgentCore Gateway (1):**
- MCP protocol with AWS_IAM authorizer
- 14 tool targets (1 target per tool)

**Configuration Storage:**
- **Parameter Store**: AgentCore Memory ID, DynamoDB table, S3 bucket, Gateway URL, AWS Region
- **Secrets Manager**: Tavily API key, Google credentials, LangChain API key (optional)

**IAM Resources:**
- Lambda execution role with CloudWatch Logs + Secrets Manager access
- Gateway role for Lambda invocation

**Monitoring:**
- CloudWatch Logs for all Lambda functions (7 days retention)

## 📝 Deployment Outputs

After successful deployment, you'll see comprehensive output:

```
✅ Deployment Complete!

📦 Deployed Lambda Functions:
  ✅ tavily: arn:aws:lambda:us-west-2:xxx:function:research-gateway-tavily-xxx
  ✅ wikipedia: arn:aws:lambda:us-west-2:xxx:function:research-gateway-wikipedia-xxx
  ...

🌐 Gateway Configuration:
  Gateway URL: https://gateway-xxx.execute-api.us-west-2.amazonaws.com
  Gateway ID: xxxxx

📋 Parameter Store Configuration:
  ✅ agentcore_memory_id: /research-gateway/{suffix}/agentcore/memory-id
  ✅ dynamodb_status_table: /research-gateway/{suffix}/dynamodb/status-table
  ✅ s3_outputs_bucket: /research-gateway/{suffix}/s3/outputs-bucket
  ✅ gateway_url: /research-gateway/{suffix}/gateway/url
  ...

🔐 Secrets Manager Configuration:
  ✅ tavily_api_key: arn:aws:secretsmanager:...
  ✅ google_credentials: arn:aws:secretsmanager:...
  ✅ langchain_api_key: arn:aws:secretsmanager:... (if configured)
```

Also saves `gateway_config.json`:
```json
{
  "gateway_url": "https://gateway-xxx.execute-api.us-west-2.amazonaws.com",
  "gateway_id": "xxxxx",
  "region": "us-west-2",
  "auth_mode": "IAM",
  "tools": ["tavily_search", "tavily_extract", ... (14 tools total)]
}
```

## 🔧 Configuration Management

### For Production (Agent Runtime)

Load configuration from AWS services:

```python
from src.utils.config_loader import load_config

config = load_config()  # Loads from Parameter Store + Secrets Manager
memory_id = config['AGENTCORE_MEMORY_ID']
gateway_url = config['GATEWAY_URL']
```

### For Local Development

Use `.env` file only (no AWS access needed):

```python
from src.utils.config_loader import load_config

config = load_config(use_aws=False)  # Loads from .env only
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for complete configuration guide.

## 💰 Cost Considerations

**Estimated Monthly Cost** (moderate usage, ~10,000 requests/month):

- Lambda: ~$3-5 (based on execution time and memory)
- Gateway: ~$2-5 (based on requests and data transfer)
- Secrets Manager: ~$2-3 ($0.40/secret/month × 2-3 secrets)
- Parameter Store: Free (standard parameters)
- CloudWatch Logs: ~$1

**Total: ~$8-15/month**

Free tier covers much of this for first year/low usage.

## 🐛 Troubleshooting

### Deployment Fails - Missing Configuration

**Problem**: `❌ AGENTCORE_MEMORY_ID not found`

**Solution**: Ensure `.env` file in parent directory contains all required values:
```bash
cd /path/to/dimensional-research-agent
cat .env  # Verify AGENTCORE_MEMORY_ID, DYNAMODB_STATUS_TABLE, S3_OUTPUTS_BUCKET exist
```

### Optional Configuration Not Working

**Problem**: LangSmith tracing not working

**Solution**: Check if `LANGCHAIN_API_KEY` is set in `.env`. If not set, tracing is disabled but deployment continues successfully.

### Build Errors

**Problem**: `duckduckgo-search==7.0.0` not found

**Solution**: Already fixed in latest code. If you see this, update to `ddgs>=9.0.0` in `lambdas/duckduckgo/requirements.txt`

### Lambda Timeout

**Problem**: Lambda times out during execution

**Solution**: Increase timeout in `terraform/variables.tf`:
```hcl
variable "lambda_timeout" {
  default = 120  # Increase from 60 to 120 seconds
}
```

### Gateway Connection Failed

**Problem**: Can't connect to Gateway

**Solution**:
1. Verify IAM permissions for agent runtime (needs `bedrock-agentcore:InvokeGateway`)
2. Check Gateway URL is correct: `terraform output gateway_url`
3. Ensure using AWS credentials with proper permissions

### Parameter Store Access Issues

**Problem**: Agent can't load configuration from Parameter Store

**Solution**:
1. Verify parameters exist:
   ```bash
   aws ssm describe-parameters \
     --parameter-filters "Key=Name,Option=BeginsWith,Values=/research-gateway/"
   ```
2. Check IAM permissions include `ssm:GetParameter`
3. For local development, use `load_config(use_aws=False)` to use `.env` only

## 📚 Related Documentation

- [Configuration Management Guide](docs/CONFIGURATION.md) - Complete config management details
- [Parent Project README](../README.md) - Main research agent documentation

## 🎯 Next Steps

1. **Deploy**: Run `./scripts/deploy.sh`
2. **Test**: Run `python scripts/test-gateway-simple.py`
3. **Integrate**: Update agent runtime to use `src/utils/config_loader.py`
4. **Monitor**: Check CloudWatch Logs for function execution
5. **Scale**: Adjust Lambda timeout/memory as needed
