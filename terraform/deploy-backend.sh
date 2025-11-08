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

# Setup .env file
setup_env_file() {
    local project_root="$(cd "${SCRIPT_DIR}/.." && pwd)"
    local env_file="${project_root}/.env"
    local env_example="${project_root}/.env.example"

    # If .env doesn't exist, create it from .env.example
    if [ ! -f "$env_file" ]; then
        if [ ! -f "$env_example" ]; then
            log_error ".env.example not found at $env_example"
            exit 1
        fi

        log_info "Creating .env file from .env.example..."
        cp "$env_example" "$env_file"
        log_info ".env file created at $env_file"
    fi

    # Update AWS_REGION from environment if set
    if [ -n "$AWS_REGION" ]; then
        sed -i.bak "s|^AWS_REGION=.*|AWS_REGION=$AWS_REGION|" "$env_file"
        rm -f "${env_file}.bak"
        log_info "AWS_REGION set to: $AWS_REGION"
    fi

    # Check and prompt for required/recommended values
    echo ""
    echo "Checking environment configuration..."
    echo ""

    local needs_input=false

    # Check TAVILY_API_KEY (recommended)
    if ! grep -q "^TAVILY_API_KEY=." "$env_file" 2>/dev/null; then
        needs_input=true
    fi

    # Check LANGCHAIN_API_KEY (optional)
    if ! grep -q "^LANGCHAIN_API_KEY=." "$env_file" 2>/dev/null; then
        needs_input=true
    fi

    if [ "$needs_input" = true ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Optional API Keys Configuration"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "These API keys are optional but recommended for better research quality."
        echo "You can skip them now and add them later to the .env file."
        echo ""

        # Prompt for TAVILY_API_KEY
        if ! grep -q "^TAVILY_API_KEY=." "$env_file" 2>/dev/null; then
            echo "1. Tavily AI Search (RECOMMENDED)"
            echo "   - High-quality AI-powered search"
            echo "   - Sign up: https://tavily.com/"
            echo "   - Free tier: 1000 searches/month"
            echo ""
            read -p "Enter TAVILY_API_KEY (or press Enter to skip): " tavily_key
            if [ -n "$tavily_key" ]; then
                sed -i.bak "s|^TAVILY_API_KEY=.*|TAVILY_API_KEY=$tavily_key|" "$env_file"
                log_info "TAVILY_API_KEY configured"
            else
                log_warn "TAVILY_API_KEY skipped (using DuckDuckGo fallback)"
            fi
            echo ""
        fi

        # Prompt for LANGCHAIN_API_KEY
        if ! grep -q "^LANGCHAIN_API_KEY=." "$env_file" 2>/dev/null; then
            echo "2. LangSmith Tracing (OPTIONAL)"
            echo "   - For debugging and monitoring workflows"
            echo "   - Sign up: https://smith.langchain.com/"
            echo ""
            read -p "Enter LANGCHAIN_API_KEY (or press Enter to skip): " langchain_key
            if [ -n "$langchain_key" ]; then
                sed -i.bak "s|^LANGCHAIN_API_KEY=.*|LANGCHAIN_API_KEY=$langchain_key|" "$env_file"
                sed -i.bak "s|^LANGCHAIN_TRACING_V2=.*|LANGCHAIN_TRACING_V2=true|" "$env_file"
                log_info "LANGCHAIN_API_KEY configured"
            else
                log_warn "LANGCHAIN_API_KEY skipped"
            fi
            echo ""
        fi

        # Prompt for Google Search API
        echo "3. Google Custom Search (OPTIONAL)"
        echo "   - Requires both API key and Search Engine ID"
        echo "   - Sign up: https://developers.google.com/custom-search"
        echo ""
        read -p "Enter GOOGLE_API_KEY (or press Enter to skip): " google_key
        if [ -n "$google_key" ]; then
            read -p "Enter GOOGLE_SEARCH_ENGINE_ID: " google_id
            if [ -n "$google_id" ]; then
                sed -i.bak "s|^GOOGLE_API_KEY=.*|GOOGLE_API_KEY=$google_key|" "$env_file"
                sed -i.bak "s|^GOOGLE_SEARCH_ENGINE_ID=.*|GOOGLE_SEARCH_ENGINE_ID=$google_id|" "$env_file"
                log_info "Google Search API configured"
            else
                log_warn "Google Search Engine ID not provided, skipping"
            fi
        else
            log_warn "Google Search API skipped"
        fi
        echo ""

        # Clean up backup files
        rm -f "${env_file}.bak"

        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
    else
        log_info "Environment configuration looks good"
        echo ""
    fi
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

# Import existing resources if found
import_existing_resources() {
    echo ""
    echo "Checking for existing resources to import..."

    cd "$BACKEND_DIR"

    # Get AWS region
    local region="${AWS_REGION:-${TF_VAR_aws_region:-us-west-2}}"

    # Calculate suffix
    local account_id=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    local suffix=$(echo -n "${account_id}" | md5sum 2>/dev/null | cut -c1-8 || echo -n "${account_id}" | md5 | cut -c1-8)

    local imported=false

    # Check and import DynamoDB tables
    if aws dynamodb describe-table --table-name "deep-research-agent-status-${suffix}" --region "$region" --no-cli-pager &>/dev/null; then
        if ! terraform state list | grep -q "aws_dynamodb_table.research_status"; then
            log_info "Importing existing status table..."
            terraform import "aws_dynamodb_table.research_status" "deep-research-agent-status-${suffix}" || log_warn "  Failed to import"
            imported=true
        fi
    fi

    if aws dynamodb describe-table --table-name "deep-research-agent-user-preferences-${suffix}" --region "$region" --no-cli-pager &>/dev/null; then
        if ! terraform state list | grep -q "aws_dynamodb_table.user_preferences"; then
            log_info "Importing existing user preferences table..."
            terraform import "aws_dynamodb_table.user_preferences" "deep-research-agent-user-preferences-${suffix}" || log_warn "  Failed to import"
            imported=true
        fi
    fi

    # Check and import S3 buckets
    if aws s3api head-bucket --bucket "deep-research-agent-outputs-${suffix}" 2>/dev/null; then
        if ! terraform state list | grep -q "aws_s3_bucket.research_outputs"; then
            log_info "Importing existing outputs bucket..."
            terraform import "aws_s3_bucket.research_outputs" "deep-research-agent-outputs-${suffix}" || log_warn "  Failed to import"
            imported=true
        fi
    fi

    if aws s3api head-bucket --bucket "deep-research-agent-codebuild-${suffix}" 2>/dev/null; then
        if ! terraform state list | grep -q "aws_s3_bucket.codebuild_artifacts"; then
            log_info "Importing existing codebuild bucket..."
            terraform import "aws_s3_bucket.codebuild_artifacts" "deep-research-agent-codebuild-${suffix}" || log_warn "  Failed to import"
            imported=true
        fi
    fi

    # Check and import Code Interpreter
    local code_interpreter_id="deep_research_code_interpreter_${suffix}"
    if aws bedrock-agentcore get-code-interpreter --code-interpreter-id "$code_interpreter_id" --region "$region" --no-cli-pager &>/dev/null; then
        if ! terraform state list | grep -q "aws_bedrockagentcore_code_interpreter.research_code_interpreter"; then
            log_info "Importing existing code interpreter..."
            terraform import "aws_bedrockagentcore_code_interpreter.research_code_interpreter" "$code_interpreter_id" || log_warn "  Failed to import"
            imported=true
        fi
    fi

    # Check and import Memory resources
    local research_memory_id="deep_research_memory_${suffix}"
    local memories=$(aws bedrock-agentcore list-memories --region "$region" --no-cli-pager 2>/dev/null | jq -r '.memories[].memoryId' 2>/dev/null || echo "")

    if echo "$memories" | grep -q "^${research_memory_id}$"; then
        if ! terraform state list | grep -q "aws_bedrockagentcore_memory.research_memory"; then
            log_info "Importing existing research memory..."
            terraform import "aws_bedrockagentcore_memory.research_memory" "$research_memory_id" || log_warn "  Failed to import"
            imported=true
        fi
    fi

    local chat_memory_id="deep_research_chat_memory_${suffix}"
    if echo "$memories" | grep -q "^${chat_memory_id}$"; then
        if ! terraform state list | grep -q "aws_bedrockagentcore_memory.chat_memory"; then
            log_info "Importing existing chat memory..."
            terraform import "aws_bedrockagentcore_memory.chat_memory" "$chat_memory_id" || log_warn "  Failed to import"
            imported=true
        fi
    fi

    if [ "$imported" = true ]; then
        log_info "Existing resources imported into Terraform state"
    else
        log_info "No existing resources to import"
    fi
    echo ""
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
    setup_env_file
    load_env_file
    check_prerequisites
    import_existing_resources
    deploy_infrastructure
    display_outputs
}

# Run main
main
