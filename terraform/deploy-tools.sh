#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/tools"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load .env file if it exists
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${BLUE}📄 Loading environment variables from .env${NC}"
    # Export variables from .env file
    set -a
    source "$ENV_FILE"
    set +a
    echo -e "${GREEN}✅ .env file loaded${NC}"
else
    echo -e "${YELLOW}⚠️  No .env file found at $ENV_FILE${NC}"
fi

echo -e "${GREEN}🚀 Research Gateway Lambda + Gateway Deployment${NC}"
echo "=================================================="

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform is not installed${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account: $ACCOUNT_ID${NC}"

# Validate required configuration from parent deployment
echo ""
echo "📋 Validating configuration from parent deployment..."

if [ -z "$AGENTCORE_MEMORY_ID" ]; then
    echo -e "${RED}❌ AGENTCORE_MEMORY_ID not found${NC}"
    echo "   Please set it in .env file from parent Terraform deployment"
    exit 1
fi
echo -e "${GREEN}✅ AGENTCORE_MEMORY_ID: ${AGENTCORE_MEMORY_ID}${NC}"

if [ -z "$DYNAMODB_STATUS_TABLE" ]; then
    echo -e "${RED}❌ DYNAMODB_STATUS_TABLE not found${NC}"
    echo "   Please set it in .env file from parent Terraform deployment"
    exit 1
fi
echo -e "${GREEN}✅ DYNAMODB_STATUS_TABLE: ${DYNAMODB_STATUS_TABLE}${NC}"

if [ -z "$S3_OUTPUTS_BUCKET" ]; then
    echo -e "${RED}❌ S3_OUTPUTS_BUCKET not found${NC}"
    echo "   Please set it in .env file from parent Terraform deployment"
    exit 1
fi
echo -e "${GREEN}✅ S3_OUTPUTS_BUCKET: ${S3_OUTPUTS_BUCKET}${NC}"

# Validate required API Keys
echo ""
echo "📋 Validating API Keys..."

if [ -z "$TAVILY_API_KEY" ]; then
    echo -e "${RED}❌ TAVILY_API_KEY not found${NC}"
    echo "   Please set it in .env file or environment variable"
    exit 1
fi
echo -e "${GREEN}✅ TAVILY_API_KEY: ${TAVILY_API_KEY:0:10}...${NC}"

# Google API credentials (optional)
if [ -z "$GOOGLE_API_KEY" ] || [ -z "$GOOGLE_SEARCH_ENGINE_ID" ]; then
    echo -e "${YELLOW}⚠️  Google API credentials not set (optional)${NC}"
    GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"
    GOOGLE_SEARCH_ENGINE_ID="${GOOGLE_SEARCH_ENGINE_ID:-}"
else
    echo -e "${GREEN}✅ GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:10}...${NC}"
    echo -e "${GREEN}✅ GOOGLE_SEARCH_ENGINE_ID: ${GOOGLE_SEARCH_ENGINE_ID}${NC}"
fi

# LangChain/LangSmith configuration (optional)
echo ""
echo "📋 Checking LangSmith configuration (optional)..."
if [ -n "$LANGCHAIN_API_KEY" ]; then
    echo -e "${GREEN}✅ LANGCHAIN_API_KEY: ${LANGCHAIN_API_KEY:0:10}...${NC}"
    echo -e "${GREEN}✅ LANGCHAIN_PROJECT: ${LANGCHAIN_PROJECT:-research-agent}${NC}"
    echo -e "${GREEN}✅ LANGCHAIN_TRACING_V2: ${LANGCHAIN_TRACING_V2:-true}${NC}"
else
    echo -e "${YELLOW}⚠️  LangSmith configuration not set (optional)${NC}"
fi

# Step 1: Build all Lambda packages
echo ""
echo "📦 Step 1: Building all Lambda packages..."
"$PROJECT_ROOT/scripts/build-all-lambdas.sh"

# Step 1.5: Build Finance Lambda Container Image
echo ""
echo "🐳 Step 1.5: Building Finance Lambda Container Image..."
"$PROJECT_ROOT/scripts/build-finance-container.sh"

# Step 2: Terraform init
echo ""
echo "🔧 Step 2: Initializing Terraform..."
cd "$TERRAFORM_DIR"

# Ensure we have the correct provider versions (6.19+)
if [ ! -f .terraform.lock.hcl ]; then
    echo "   Creating provider lock file with version 6.19..."
    terraform providers lock -platform=darwin_arm64 -platform=linux_amd64 hashicorp/aws hashicorp/random
fi

echo "   Initializing Terraform..."
terraform init

# Step 3: Terraform apply (auto-approved)
echo ""
echo "🚀 Step 3: Applying Terraform..."
terraform apply -auto-approve \
    -var="agentcore_memory_id=$AGENTCORE_MEMORY_ID" \
    -var="dynamodb_status_table=$DYNAMODB_STATUS_TABLE" \
    -var="s3_outputs_bucket=$S3_OUTPUTS_BUCKET" \
    -var="tavily_api_key=$TAVILY_API_KEY" \
    -var="google_api_key=$GOOGLE_API_KEY" \
    -var="google_search_engine_id=$GOOGLE_SEARCH_ENGINE_ID" \
    -var="langchain_api_key=${LANGCHAIN_API_KEY:-}" \
    -var="langchain_project=${LANGCHAIN_PROJECT:-}" \
    -var="langchain_tracing_v2=${LANGCHAIN_TRACING_V2:-}"

# Step 4: Output results
echo ""
echo "=================================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=================================================="

echo ""
echo "📦 Deployed Lambda Functions:"
terraform output -json all_lambda_arns | jq -r 'to_entries[] | "  ✅ \(.key): \(.value)"'

# Check if gateway outputs exist
if terraform output gateway_url &> /dev/null; then
    echo ""
    echo "🌐 Gateway Configuration:"
    GATEWAY_URL=$(terraform output -raw gateway_url)
    GATEWAY_ID=$(terraform output -raw gateway_id)

    echo "  Gateway URL: $GATEWAY_URL"
    echo "  Gateway ID:  $GATEWAY_ID"

    # Save gateway config
    CONFIG_FILE="$(dirname "$SCRIPT_DIR")/gateway_config.json"
    terraform output -json gateway_config > "$CONFIG_FILE"
    echo ""
    echo -e "${GREEN}✅ Gateway config saved to: $CONFIG_FILE${NC}"
fi

# Display Parameter Store configuration
echo ""
echo "📋 Parameter Store Configuration:"
echo "   Configuration values stored in AWS Systems Manager Parameter Store:"
terraform output -json parameter_store_config | jq -r 'to_entries[] | select(.value != null) | "  ✅ \(.key): \(.value)"'

# Display Secrets Manager configuration
echo ""
echo "🔐 Secrets Manager Configuration:"
echo "   API keys and secrets stored in AWS Secrets Manager (ARNs hidden for security):"
echo "  ✅ tavily_api_key: [Secret stored in AWS Secrets Manager]"
echo "  ✅ google_credentials: [Secret stored in AWS Secrets Manager]"
if [ -n "$LANGCHAIN_API_KEY" ]; then
    echo "  ✅ langchain_api_key: [Secret stored in AWS Secrets Manager]"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}📝 Configuration Management${NC}"
echo "=================================================="
echo ""
echo "Your agent runtime should load configuration as follows:"
echo ""
echo "1. 📋 Parameter Store (non-sensitive config):"
echo "   - AGENTCORE_MEMORY_ID"
echo "   - DYNAMODB_STATUS_TABLE"
echo "   - S3_OUTPUTS_BUCKET"
echo "   - GATEWAY_URL"
echo "   - AWS_REGION"
echo ""
echo "2. 🔐 Secrets Manager (sensitive data):"
echo "   - TAVILY_API_KEY"
echo "   - GOOGLE_API_KEY (if configured)"
echo "   - LANGCHAIN_API_KEY (if configured)"
echo ""
echo "3. 📄 Local .env (for development):"
echo "   - All values can be kept in .env for local testing"
echo "   - No need for .bedrock_agentcore.yaml anymore"
echo ""
echo "Next steps:"
echo "  1. Test Gateway: python terraform/tools/scripts/test-gateway-simple.py"
echo "  2. View logs: aws logs tail /aws/lambda/<function-name> --follow"
echo "  3. Update agent runtime to load from Parameter Store/Secrets Manager"
