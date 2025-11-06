#!/bin/bash
set -e

# Deep Research Agent - Backend Deployment Script
# Deploys: AgentCore Runtime + DynamoDB + S3 + ECR + CodeBuild

echo "========================================"
echo "Deep Research Agent - Backend Deploy"
echo "========================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="${SCRIPT_DIR}/backend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Load .env file if it exists
load_env_file() {
    local env_file="${1:-.env}"

    if [ ! -f "$env_file" ]; then
        log_error ".env file not found at $env_file"
        exit 1
    fi

    log_info "Loading environment variables from $env_file"

    # Export each line as TF_VAR_* for Terraform
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue

        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)

        # Map .env variables to Terraform variables
        case "$key" in
            "AWS_REGION")
                export TF_VAR_aws_region="$value"
                ;;
            "LANGCHAIN_API_KEY")
                export TF_VAR_langchain_api_key="$value"
                ;;
            "LANGCHAIN_TRACING_V2")
                export TF_VAR_langchain_tracing_enabled="$value"
                ;;
            "LANGCHAIN_PROJECT")
                export TF_VAR_langchain_project="$value"
                ;;
            "TAVILY_API_KEY")
                export TF_VAR_tavily_api_key="$value"
                ;;
            "GOOGLE_API_KEY")
                export TF_VAR_google_api_key="$value"
                ;;
            "GOOGLE_SEARCH_ENGINE_ID")
                export TF_VAR_google_search_engine_id="$value"
                ;;
        esac
    done < "$env_file"

    log_info "Environment variables loaded successfully"
}

# Configuration
AWS_REGION=${TF_VAR_aws_region:-us-west-2}
ENVIRONMENT=${ENVIRONMENT:-dev}

# Check prerequisites
check_prerequisites() {
    echo ""
    echo "Checking prerequisites..."

    if ! command -v terraform &> /dev/null; then
        log_error "Terraform not found. Please install Terraform."
        exit 1
    fi
    log_info "Terraform installed"

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install AWS CLI."
        exit 1
    fi
    log_info "AWS CLI installed"

    if ! command -v zip &> /dev/null; then
        log_error "zip not found. Please install zip utility."
        exit 1
    fi
    log_info "zip utility installed"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure'."
        exit 1
    fi
    log_info "AWS credentials configured"

    log_warn "Note: Docker is NOT required locally - CodeBuild will handle image builds"
}

# Deploy all infrastructure with CodeBuild
deploy_infrastructure() {
    echo ""
    echo "========================================"
    echo "Deploying Backend Infrastructure"
    echo "========================================"
    echo ""
    echo "This will create:"
    echo "  - ECR Repository"
    echo "  - S3 Bucket for outputs"
    echo "  - DynamoDB Tables"
    echo "  - CodeBuild Project"
    echo "  - AgentCore Runtime"
    echo ""

    cd "$BACKEND_DIR"

    log_info "Initializing Terraform..."
    terraform init

    # Check if null_resource exists before tainting
    log_info "Detecting code changes..."
    if terraform state list | grep -q "null_resource.build_research_agent"; then
        log_info "Marking Research Agent for rebuild (code changes detected)..."
        terraform taint null_resource.build_research_agent || true
    fi

    if terraform state list | grep -q "null_resource.build_chat_agent"; then
        log_info "Marking Chat Agent for rebuild (code changes detected)..."
        terraform taint null_resource.build_chat_agent || true
    fi

    log_info "Applying infrastructure and building updated images..."
    terraform apply -auto-approve

    cd -
}

# Display outputs
display_outputs() {
    echo ""
    echo "========================================"
    echo "Backend Deployment Complete!"
    echo "========================================"

    cd "$BACKEND_DIR"

    echo ""
    echo "Deployment Summary:"
    terraform output -json summary | jq -r '
        "Project: \(.project_name)",
        "Environment: \(.environment)",
        "Region: \(.region)",
        "",
        "ECR Repositories:",
        "  Research Agent: \(.ecr_repositories.research_agent)",
        "  Chat Agent: \(.ecr_repositories.chat_agent)",
        "",
        "AgentCore Runtimes:",
        "  Research Agent:",
        "    ID: \(.agentcore_runtimes.research_agent.id)",
        "    Status: \(.agentcore_runtimes.research_agent.status)",
        "    Version: \(.agentcore_runtimes.research_agent.version)",
        "  Chat Agent:",
        "    ID: \(.agentcore_runtimes.chat_agent.id)",
        "    Status: \(.agentcore_runtimes.chat_agent.status)",
        "    Version: \(.agentcore_runtimes.chat_agent.version)",
        "",
        "DynamoDB Tables:",
        "  Status: \(.dynamodb_tables.status)",
        "  User Preferences: \(.dynamodb_tables.user_preferences)",
        "",
        "S3 Bucket: \(.s3_bucket)",
        "",
        "IAM Role: \(.iam_role_arn)"
    '

    echo ""
    echo "Individual Outputs (for reference):"
    echo "  Research Runtime ID: $(terraform output -raw agent_runtime_id)"
    echo "  Chat Runtime ID: $(terraform output -raw chat_agent_runtime_id)"
    echo "  Status Table: $(terraform output -raw dynamodb_status_table)"
    echo "  User Preferences Table: $(terraform output -raw dynamodb_user_preferences_table)"

    cd -

    echo ""
    log_info "Backend deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy frontend: ./deploy-frontend.sh"
    echo "  2. Or deploy tools: ./deploy-tools.sh (coming soon)"
    echo "  3. Test research workflow invocation"
    echo "  4. Monitor CloudWatch Logs"
}

# Main deployment flow
main() {
    load_env_file
    check_prerequisites
    deploy_infrastructure
    display_outputs
}

# Run main
main
