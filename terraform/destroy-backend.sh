#!/bin/bash
set -e

# Deep Research Agent - Backend Destroy Script
# Destroys: AgentCore Runtime + DynamoDB + S3 + ECR + CodeBuild

echo "========================================"
echo "Deep Research Agent - Backend Destroy"
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
        log_warn ".env file not found at $env_file (skipping)"
        return
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

# Check if backend exists
check_backend_exists() {
    if [ ! -d "$BACKEND_DIR" ]; then
        log_error "Backend directory not found at $BACKEND_DIR"
        exit 1
    fi

    if [ ! -f "$BACKEND_DIR/terraform.tfstate" ]; then
        log_warn "Backend terraform state not found. Nothing to destroy."
        exit 0
    fi

    log_info "Backend infrastructure found"
}

# Confirm destruction (only if called directly, not from main destroy.sh)
confirm_destruction() {
    # Skip confirmation if called from main orchestrator
    if [ "$SKIP_CONFIRM" = "1" ]; then
        return
    fi

    echo ""
    echo -e "${RED}⚠️  WARNING: This will permanently destroy:${NC}"
    echo "  - AgentCore Runtime (Research Agent)"
    echo "  - AgentCore Runtime (Chat Agent)"
    echo "  - ECR Repositories and all images"
    echo "  - DynamoDB Tables (status, user preferences)"
    echo "  - S3 Buckets and contents"
    echo "  - CodeBuild Projects"
    echo "  - IAM Roles and Policies"
    echo ""
    echo -e "${RED}This action CANNOT be undone!${NC}"
    echo ""

    read -p "Are you sure you want to destroy the backend? (type 'destroy' to confirm): " CONFIRM

    if [ "$CONFIRM" != "destroy" ]; then
        echo ""
        log_info "Backend destruction cancelled"
        exit 0
    fi
}

# Pre-destroy cleanup
pre_destroy_cleanup() {
    echo ""
    echo "========================================"
    echo "Pre-Destroy Cleanup"
    echo "========================================"

    cd "$BACKEND_DIR"

    # Delete ECR repositories and all images
    log_info "Deleting ECR repositories and all images..."

    # Get AWS region from terraform or environment
    AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "${TF_VAR_aws_region:-us-east-1}")

    # Find all ECR repositories starting with "bedrock/deep-research-agent"
    log_info "Searching for deep-research-agent ECR repositories in region: $AWS_REGION"

    ECR_REPOS=$(aws ecr describe-repositories \
        --region "$AWS_REGION" \
        --no-cli-pager \
        2>/dev/null | jq -r '.repositories[] | select(.repositoryName | startswith("bedrock/deep-research-agent")) | .repositoryName' || echo "")

    if [ -n "$ECR_REPOS" ]; then
        while IFS= read -r repo; do
            if [ -n "$repo" ]; then
                log_info "Deleting ECR repository: $repo"
                aws ecr delete-repository \
                    --repository-name "$repo" \
                    --force \
                    --region "$AWS_REGION" \
                    --no-cli-pager > /dev/null 2>&1 && log_info "  ✓ Deleted" || log_warn "  Failed or already deleted"
            fi
        done <<< "$ECR_REPOS"
        log_info "All ECR repositories processed"
    else
        log_warn "No ECR repositories found (may already be deleted)"
    fi

    # Empty S3 buckets (Terraform will delete them)
    log_info "Emptying S3 buckets..."

    # Get bucket names from state
    S3_OUTPUTS_BUCKET=$(terraform state show 'aws_s3_bucket.research_outputs' 2>/dev/null | grep -E '^\s*id\s*=' | awk -F'"' '{print $2}')
    S3_CODEBUILD_BUCKET=$(terraform state show 'aws_s3_bucket.codebuild_artifacts' 2>/dev/null | grep -E '^\s*id\s*=' | awk -F'"' '{print $2}')

    for bucket in "$S3_OUTPUTS_BUCKET" "$S3_CODEBUILD_BUCKET"; do
        if [ -n "$bucket" ] && [ "$bucket" != "" ]; then
            log_info "Emptying bucket: $bucket"

            # Check if bucket exists
            if aws s3 ls "s3://${bucket}" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
                # Empty bucket (Terraform will delete it)
                aws s3 rm "s3://${bucket}" --recursive --region "$AWS_REGION" --no-cli-pager 2>&1 | grep -v "^$" || true
                log_info "  ✓ Emptied bucket: $bucket"
            else
                log_warn "  Bucket $bucket not found"
            fi
        fi
    done

    # Delete AgentCore Runtimes first (they depend on Memory)
    log_info "Deleting AgentCore Runtimes..."

    RESEARCH_RUNTIME_ID=$(terraform state show 'awscc_bedrockagentcore_runtime.research_agent' 2>/dev/null | grep -E '^\s*agent_runtime_id\s*=' | awk -F'"' '{print $2}')
    CHAT_RUNTIME_ID=$(terraform state show 'awscc_bedrockagentcore_runtime.chat_agent' 2>/dev/null | grep -E '^\s*agent_runtime_id\s*=' | awk -F'"' '{print $2}')

    if [ -n "$RESEARCH_RUNTIME_ID" ] && [ "$RESEARCH_RUNTIME_ID" != "" ]; then
        log_info "Deleting research agent runtime: $RESEARCH_RUNTIME_ID"
        aws bedrock-agentcore delete-agent-runtime \
            --agent-runtime-id "$RESEARCH_RUNTIME_ID" \
            --region "$AWS_REGION" \
            --no-cli-pager > /dev/null 2>&1 && log_info "  ✓ Deleted" || log_warn "  Failed or already deleted"

        # Wait a bit for deletion to propagate
        sleep 5
    fi

    if [ -n "$CHAT_RUNTIME_ID" ] && [ "$CHAT_RUNTIME_ID" != "" ]; then
        log_info "Deleting chat agent runtime: $CHAT_RUNTIME_ID"
        aws bedrock-agentcore delete-agent-runtime \
            --agent-runtime-id "$CHAT_RUNTIME_ID" \
            --region "$AWS_REGION" \
            --no-cli-pager > /dev/null 2>&1 && log_info "  ✓ Deleted" || log_warn "  Failed or already deleted"

        # Wait a bit for deletion to propagate
        sleep 5
    fi

    log_info "Pre-destroy cleanup complete"
}

# Import ALL orphaned resources (any suffix) into Terraform state
import_all_orphaned_resources() {
    echo ""
    log_info "Searching for ALL orphaned resources to import..."

    cd "$BACKEND_DIR"

    local imported=false

    # Find and import ALL DynamoDB tables
    log_info "Searching for DynamoDB tables..."
    local all_status_tables=$(aws dynamodb list-tables --region "$AWS_REGION" --no-cli-pager 2>/dev/null | jq -r '.TableNames[] | select(startswith("deep-research-agent-status"))' || echo "")
    local all_prefs_tables=$(aws dynamodb list-tables --region "$AWS_REGION" --no-cli-pager 2>/dev/null | jq -r '.TableNames[] | select(startswith("deep-research-agent-user-preferences"))' || echo "")

    # Import first status table found (Terraform can only have one in state)
    if [ -n "$all_status_tables" ]; then
        local first_table=$(echo "$all_status_tables" | head -1)
        if [ -n "$first_table" ] && ! terraform state list | grep -q "aws_dynamodb_table.research_status"; then
            log_info "Importing status table: $first_table"
            terraform import "aws_dynamodb_table.research_status" "$first_table" 2>/dev/null && imported=true || log_warn "  Failed"
        fi
    fi

    # Import first prefs table found
    if [ -n "$all_prefs_tables" ]; then
        local first_table=$(echo "$all_prefs_tables" | head -1)
        if [ -n "$first_table" ] && ! terraform state list | grep -q "aws_dynamodb_table.user_preferences"; then
            log_info "Importing user preferences table: $first_table"
            terraform import "aws_dynamodb_table.user_preferences" "$first_table" 2>/dev/null && imported=true || log_warn "  Failed"
        fi
    fi

    # Find and import S3 buckets
    log_info "Searching for S3 buckets..."
    local all_output_buckets=$(aws s3 ls 2>/dev/null | grep "deep-research-agent-outputs" | awk '{print $3}' || echo "")
    local all_codebuild_buckets=$(aws s3 ls 2>/dev/null | grep "deep-research-agent-codebuild" | awk '{print $3}' || echo "")

    if [ -n "$all_output_buckets" ]; then
        local first_bucket=$(echo "$all_output_buckets" | head -1)
        if [ -n "$first_bucket" ] && ! terraform state list | grep -q "aws_s3_bucket.research_outputs"; then
            log_info "Importing outputs bucket: $first_bucket"
            terraform import "aws_s3_bucket.research_outputs" "$first_bucket" 2>/dev/null && imported=true || log_warn "  Failed"
        fi
    fi

    if [ -n "$all_codebuild_buckets" ]; then
        local first_bucket=$(echo "$all_codebuild_buckets" | head -1)
        if [ -n "$first_bucket" ] && ! terraform state list | grep -q "aws_s3_bucket.codebuild_artifacts"; then
            log_info "Importing codebuild bucket: $first_bucket"
            terraform import "aws_s3_bucket.codebuild_artifacts" "$first_bucket" 2>/dev/null && imported=true || log_warn "  Failed"
        fi
    fi

    # Find and import Code Interpreters
    log_info "Searching for Code Interpreters..."
    local all_cis=$(aws bedrock-agentcore list-code-interpreters --region "$AWS_REGION" --no-cli-pager 2>/dev/null | jq -r '.codeInterpreters[]? | select(.codeInterpreterName | startswith("deep_research")) | .codeInterpreterName' || echo "")

    if [ -n "$all_cis" ]; then
        local first_ci=$(echo "$all_cis" | head -1)
        if [ -n "$first_ci" ] && ! terraform state list | grep -q "aws_bedrockagentcore_code_interpreter.research_code_interpreter"; then
            log_info "Importing code interpreter: $first_ci"
            terraform import "aws_bedrockagentcore_code_interpreter.research_code_interpreter" "$first_ci" 2>/dev/null && imported=true || log_warn "  Failed"
        fi
    fi

    # Find and import Memories
    log_info "Searching for Memories..."
    local all_memories=$(aws bedrock-agentcore list-memories --region "$AWS_REGION" --no-cli-pager 2>/dev/null | jq -r '.memories[]? | select(.memoryId | startswith("deep_research")) | .memoryId' || echo "")

    if [ -n "$all_memories" ]; then
        local research_memories=$(echo "$all_memories" | grep -v "chat")
        local chat_memories=$(echo "$all_memories" | grep "chat")

        if [ -n "$research_memories" ]; then
            local first_mem=$(echo "$research_memories" | head -1)
            if [ -n "$first_mem" ] && ! terraform state list | grep -q "aws_bedrockagentcore_memory.research_memory"; then
                log_info "Importing research memory: $first_mem"
                terraform import "aws_bedrockagentcore_memory.research_memory" "$first_mem" 2>/dev/null && imported=true || log_warn "  Failed"
            fi
        fi

        if [ -n "$chat_memories" ]; then
            local first_mem=$(echo "$chat_memories" | head -1)
            if [ -n "$first_mem" ] && ! terraform state list | grep -q "aws_bedrockagentcore_memory.chat_memory"; then
                log_info "Importing chat memory: $first_mem"
                terraform import "aws_bedrockagentcore_memory.chat_memory" "$first_mem" 2>/dev/null && imported=true || log_warn "  Failed"
            fi
        fi
    fi

    if [ "$imported" = true ]; then
        log_info "Orphaned resources imported - Terraform will now manage them"
    else
        log_info "No orphaned resources found to import"
    fi
    echo ""
}

# Destroy infrastructure
destroy_infrastructure() {
    echo ""
    echo "========================================"
    echo "Destroying Backend Infrastructure"
    echo "========================================"

    cd "$BACKEND_DIR"

    log_info "Initializing Terraform..."
    terraform init

    # Remove Runtime resources from state (already deleted manually)
    log_info "Removing Runtime resources from Terraform state..."
    terraform state rm 'awscc_bedrockagentcore_runtime.research_agent' 2>/dev/null || true
    terraform state rm 'awscc_bedrockagentcore_runtime.chat_agent' 2>/dev/null || true

    log_warn "Running Terraform destroy..."
    terraform destroy -auto-approve

    log_info "Backend infrastructure destroyed"
}

# Cleanup local files
cleanup_local_files() {
    echo ""
    echo "Cleaning up local files..."

    # Clean up Lambda zip files if they exist
    if [ -d "$SCRIPT_DIR/../lambda" ]; then
        log_info "Cleaning Lambda build artifacts..."
        find "$SCRIPT_DIR/../lambda" -name "*.zip" -delete 2>/dev/null || true
    fi

    log_info "Local cleanup complete"
}

# Display completion message
display_completion() {
    echo ""
    echo "========================================"
    log_info "Backend Destruction Complete!"
    echo "========================================"
    echo ""
    echo "All backend resources have been removed from AWS."
    echo ""
}

# Main destruction flow
main() {
    load_env_file
    check_backend_exists
    confirm_destruction
    pre_destroy_cleanup
    import_all_orphaned_resources
    destroy_infrastructure
    cleanup_local_files
    display_completion
}

# Run main
main
