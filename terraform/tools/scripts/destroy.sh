#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}🗑️  Destroying Research Gateway Infrastructure${NC}"
echo "=================================================="
echo ""

# Skip confirmation if called from main orchestrator
if [ "$SKIP_CONFIRM" != "1" ]; then
    echo -e "${YELLOW}⚠️  WARNING: This will destroy:${NC}"
    echo "  - AgentCore Gateway"
    echo "  - Lambda functions"
    echo "  - IAM roles and policies"
    echo "  - Secrets Manager secrets"
    echo ""

    read -p "Are you sure? (type 'destroy' to confirm): " CONFIRM

    if [ "$CONFIRM" != "destroy" ]; then
        echo -e "${RED}❌ Destruction cancelled${NC}"
        exit 0
    fi
fi

cd "$TERRAFORM_DIR"

echo ""
echo "🗑️  Removing build triggers to prevent rebuilds during destroy..."
# Remove null_resource triggers that cause Lambda builds
terraform state list | grep "null_resource" | while read resource; do
    echo "  Removing: $resource"
    terraform state rm "$resource" 2>/dev/null || true
done

echo ""
echo "🗑️  Extracting variables from state..."
# Extract required variables from current state to avoid prompts
MEMORY_ID=$(terraform state show -no-color 'aws_ssm_parameter.agentcore_memory_id' 2>/dev/null | grep 'value' | head -1 | awk -F'"' '{print $2}' || echo "dummy")
STATUS_TABLE=$(terraform state show -no-color 'aws_ssm_parameter.dynamodb_status_table' 2>/dev/null | grep 'value' | head -1 | awk -F'"' '{print $2}' || echo "dummy")
S3_BUCKET=$(terraform state show -no-color 'aws_ssm_parameter.s3_outputs_bucket' 2>/dev/null | grep 'value' | head -1 | awk -F'"' '{print $2}' || echo "dummy")
TAVILY_KEY=$(terraform state show -no-color 'aws_secretsmanager_secret_version.tavily_api_key' 2>/dev/null | grep 'secret_string' | head -1 | awk -F'"' '{print $2}' || echo "dummy")

echo ""
echo "🗑️  Running Terraform destroy..."
terraform destroy -auto-approve \
  -var="agentcore_memory_id=${MEMORY_ID}" \
  -var="dynamodb_status_table=${STATUS_TABLE}" \
  -var="s3_outputs_bucket=${S3_BUCKET}" \
  -var="tavily_api_key=${TAVILY_KEY}"

echo ""
echo "🧹 Cleaning up build artifacts..."
rm -rf "$PROJECT_ROOT/build"
rm -f "$PROJECT_ROOT/gateway_config.json"

echo ""
echo -e "${RED}✅ All resources destroyed${NC}"
