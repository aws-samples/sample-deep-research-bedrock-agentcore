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

    # Empty S3 buckets before destroy
    log_info "Emptying S3 buckets..."

    # Get bucket names from state
    S3_OUTPUTS_BUCKET=$(terraform state show 'aws_s3_bucket.research_outputs' 2>/dev/null | grep -E '^\s*id\s*=' | awk -F'"' '{print $2}')
    S3_CODEBUILD_BUCKET=$(terraform state show 'aws_s3_bucket.codebuild_artifacts' 2>/dev/null | grep -E '^\s*id\s*=' | awk -F'"' '{print $2}')

    for bucket in "$S3_OUTPUTS_BUCKET" "$S3_CODEBUILD_BUCKET"; do
        if [ -n "$bucket" ] && [ "$bucket" != "" ]; then
            log_info "Emptying bucket: $bucket"

            # Check if bucket exists
            if aws s3 ls "s3://${bucket}" --no-cli-pager > /dev/null 2>&1; then
                # Delete all objects
                log_info "  Deleting objects..."
                aws s3 rm "s3://${bucket}" --recursive --no-cli-pager 2>&1 | grep -v "^$" || true

                # Delete all object versions (if versioning enabled)
                log_info "  Deleting versions..."
                aws s3api delete-objects \
                    --bucket "$bucket" \
                    --delete "$(aws s3api list-object-versions \
                        --bucket "$bucket" \
                        --output json \
                        --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
                        2>/dev/null)" \
                    --no-cli-pager > /dev/null 2>&1 || true

                # Delete all delete markers
                aws s3api delete-objects \
                    --bucket "$bucket" \
                    --delete "$(aws s3api list-object-versions \
                        --bucket "$bucket" \
                        --output json \
                        --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
                        2>/dev/null)" \
                    --no-cli-pager > /dev/null 2>&1 || true

                log_info "  Bucket $bucket emptied"
            else
                log_warn "  Bucket $bucket not found or already deleted"
            fi
        fi
    done

    log_info "Pre-destroy cleanup complete"
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
    destroy_infrastructure
    cleanup_local_files
    display_completion
}

# Run main
main
