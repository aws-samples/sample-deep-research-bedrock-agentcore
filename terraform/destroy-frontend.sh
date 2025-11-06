#!/bin/bash
set -e

# Deep Research Agent - Frontend Destroy Script
# Destroys: CloudFront + ECS Fargate + Cognito + VPC + ALB

echo "=========================================="
echo "  Deep Research Agent - Frontend Destroy"
echo "=========================================="

# Get script directory and set base paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR"
FRONTEND_TF_DIR="$SCRIPT_DIR/frontend"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
        esac
    done < "$env_file"

    log_info "Environment variables loaded successfully"
}

# Check if frontend exists
check_frontend_exists() {
    if [ ! -d "$FRONTEND_TF_DIR" ]; then
        log_error "Frontend directory not found at $FRONTEND_TF_DIR"
        exit 1
    fi

    if [ ! -f "$FRONTEND_TF_DIR/terraform.tfstate" ]; then
        log_warn "Frontend terraform state not found. Nothing to destroy."
        exit 0
    fi

    log_info "Frontend infrastructure found"
}

# Confirm destruction (only if called directly, not from main destroy.sh)
confirm_destruction() {
    # Skip confirmation if called from main orchestrator
    if [ "$SKIP_CONFIRM" = "1" ]; then
        return
    fi

    echo ""
    echo -e "${RED}⚠️  WARNING: This will permanently destroy:${NC}"
    echo "  - CloudFront Distribution"
    echo "  - ECS Cluster & Fargate Service"
    echo "  - Application Load Balancer"
    echo "  - VPC (subnets, route tables, NAT gateways)"
    echo "  - ECR Repository and all images"
    echo "  - Cognito User Pool & Identity Pool"
    echo "  - All user accounts and sessions"
    echo ""
    echo -e "${RED}This action CANNOT be undone!${NC}"
    echo -e "${YELLOW}Note: CloudFront deletion can take 15-60 minutes${NC}"
    echo ""

    read -p "Are you sure you want to destroy the frontend? (type 'destroy' to confirm): " CONFIRM

    if [ "$CONFIRM" != "destroy" ]; then
        echo ""
        log_info "Frontend destruction cancelled"
        exit 0
    fi
}

# Pre-destroy cleanup
pre_destroy_cleanup() {
    echo ""
    echo "========================================"
    echo "Pre-Destroy Cleanup"
    echo "========================================"

    cd "$FRONTEND_TF_DIR"

    # Scale down ECS service to 0 to speed up deletion
    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")
    SERVICE_NAME=$(terraform output -raw ecs_service_name 2>/dev/null || echo "")

    if [ -n "$CLUSTER_NAME" ] && [ -n "$SERVICE_NAME" ]; then
        log_info "Scaling down ECS service to 0 tasks..."
        aws ecs update-service \
            --cluster "$CLUSTER_NAME" \
            --service "$SERVICE_NAME" \
            --desired-count 0 \
            --no-cli-pager > /dev/null 2>&1 || log_warn "Could not scale down ECS service"

        sleep 5
    fi

    # Delete ECR repository and all images (simpler than deleting images one by one)
    ECR_REPO_NAME=$(terraform output -raw ecr_repository_name 2>/dev/null || echo "")

    if [ -n "$ECR_REPO_NAME" ]; then
        log_info "Deleting ECR repository and all images..."

        # Force delete repository with all images at once
        aws ecr delete-repository \
            --repository-name "$ECR_REPO_NAME" \
            --force \
            --no-cli-pager > /dev/null 2>&1 || log_warn "ECR repository already deleted or not found"

        log_info "ECR repository deleted"
    fi

    log_info "Pre-destroy cleanup complete"
}

# Destroy infrastructure
destroy_infrastructure() {
    echo ""
    echo "========================================"
    echo "Destroying Frontend Infrastructure"
    echo "========================================"

    cd "$FRONTEND_TF_DIR"

    log_info "Initializing Terraform..."
    terraform init

    log_warn "Running Terraform destroy..."
    log_warn "This may take 15-60 minutes due to CloudFront..."
    terraform destroy -auto-approve

    log_info "Frontend infrastructure destroyed"
}

# Cleanup local files
cleanup_local_files() {
    echo ""
    echo "Cleaning up local files..."

    # Remove frontend config
    if [ -f "$PROJECT_ROOT/frontend-config.json" ]; then
        rm -f "$PROJECT_ROOT/frontend-config.json"
        log_info "Removed frontend-config.json"
    fi

    # Clean up frontend build artifacts
    if [ -d "$PROJECT_ROOT/frontend/build" ]; then
        rm -rf "$PROJECT_ROOT/frontend/build"
        log_info "Removed frontend build directory"
    fi

    log_info "Local cleanup complete"
}

# Display completion message
display_completion() {
    echo ""
    echo "========================================"
    log_info "Frontend Destruction Complete!"
    echo "========================================"
    echo ""
    echo "All frontend resources have been removed from AWS."
    echo ""
    echo "If you also want to destroy the backend:"
    echo "  ./destroy-backend.sh"
    echo ""
}

# Main destruction flow
main() {
    load_env_file
    check_frontend_exists
    confirm_destruction
    pre_destroy_cleanup
    destroy_infrastructure
    cleanup_local_files
    display_completion
}

# Run main
main
