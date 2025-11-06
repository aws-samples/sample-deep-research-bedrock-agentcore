#!/bin/bash
set -e

# Deep Research Agent - Frontend Deployment Script
# Deploys: CloudFront + ECS Fargate + Cognito

echo "=========================================="
echo "  Deep Research Agent - Frontend Deploy"
echo "=========================================="

# Get script directory and set base paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR"
FRONTEND_TF_DIR="$SCRIPT_DIR/frontend"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_APP_DIR="$PROJECT_ROOT/frontend"

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

    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    log_info "Docker installed"

    if ! command -v npm &> /dev/null; then
        log_error "npm not found. Please install Node.js."
        exit 1
    fi
    log_info "npm installed"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure'."
        exit 1
    fi
    log_info "AWS credentials configured"

    # Check if backend has been deployed
    BACKEND_TFSTATE="$TERRAFORM_DIR/backend/terraform.tfstate"
    if [ ! -f "$BACKEND_TFSTATE" ]; then
        log_error "Backend infrastructure not found at $BACKEND_TFSTATE"
        log_error "Please run ./deploy-backend.sh first."
        exit 1
    fi
    log_info "Backend infrastructure exists"
}

# Build React frontend
build_frontend() {
    echo ""
    echo "========================================"
    echo "Building React Frontend"
    echo "========================================"

    cd "$FRONTEND_APP_DIR"

    # Clean cache to avoid ENOTEMPTY errors
    log_info "Cleaning cache..."
    rm -rf node_modules/.cache 2>/dev/null || true

    # Check if node_modules exists, skip npm ci if already installed
    if [ ! -d "node_modules" ]; then
        log_info "Installing dependencies..."
        npm ci
    else
        log_info "Dependencies already installed, skipping npm ci"
    fi

    # Get Terraform outputs for build-time environment variables
    cd "$FRONTEND_TF_DIR"

    CLOUDFRONT_URL=$(terraform output -raw cloudfront_url)
    AWS_REGION=$(aws configure get region || echo "us-west-2")
    USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
    USER_POOL_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
    IDENTITY_POOL_ID=$(terraform output -raw cognito_identity_pool_id)

    cd "$FRONTEND_APP_DIR"

    log_info "Building React app with environment:"
    log_info "  API_URL: $CLOUDFRONT_URL"
    log_info "  REGION: $AWS_REGION"

    # Build with environment variables in a subshell to avoid polluting parent environment
    (
        export REACT_APP_API_URL="$CLOUDFRONT_URL"
        export REACT_APP_AWS_REGION="$AWS_REGION"
        export REACT_APP_USER_POOL_ID="$USER_POOL_ID"
        export REACT_APP_USER_POOL_CLIENT_ID="$USER_POOL_CLIENT_ID"
        export REACT_APP_IDENTITY_POOL_ID="$IDENTITY_POOL_ID"
        export REACT_APP_ENABLE_AUTH="true"
        npm run build
    )

    log_info "Frontend build complete!"
}

# Build and push Docker image
build_docker_image() {
    echo ""
    echo "========================================"
    echo "Building Docker Image"
    echo "========================================"

    # Get ECR repository URL from Terraform
    cd "$FRONTEND_TF_DIR"

    # Check if terraform state exists (first deploy)
    if [ ! -f "terraform.tfstate" ]; then
        log_warn "First deployment - Terraform state not found. Will create ECR during infrastructure deployment."
        return
    fi

    ECR_REPO=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")

    if [ -z "$ECR_REPO" ]; then
        log_warn "ECR repository not yet created. Skipping Docker build."
        log_warn "Run deploy again after infrastructure is created."
        return
    fi

    log_info "ECR Repository: $ECR_REPO"

    # Login to ECR
    AWS_REGION=$(aws configure get region || echo "us-west-2")
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

    log_info "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

    # Build Docker image for linux/amd64 (ECS Fargate)
    cd "$PROJECT_ROOT"
    log_info "Building Docker image..."
    docker build -f Dockerfile.frontend --platform linux/amd64 --build-arg BUILDKIT_INLINE_CACHE=1 -t $ECR_REPO:latest .

    # Push to ECR
    log_info "Pushing image to ECR..."
    docker push $ECR_REPO:latest

    log_info "Docker image pushed successfully!"
}

# Deploy infrastructure
deploy_infrastructure() {
    echo ""
    echo "========================================"
    echo "Deploying Frontend Infrastructure"
    echo "========================================"
    echo ""
    echo "This will create:"
    echo "  - VPC with public/private subnets"
    echo "  - ECS Cluster & Fargate Service"
    echo "  - Application Load Balancer"
    echo "  - CloudFront Distribution"
    echo "  - Cognito User Pool & Identity Pool"
    echo ""

    cd "$FRONTEND_TF_DIR"

    log_info "Initializing Terraform..."
    terraform init

    log_info "Applying infrastructure..."
    terraform apply -auto-approve
}

# Update ECS service (force new deployment)
update_ecs_service() {
    echo ""
    echo "========================================"
    echo "Updating ECS Service"
    echo "========================================"

    cd "$FRONTEND_TF_DIR"

    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")
    SERVICE_NAME=$(terraform output -raw ecs_service_name 2>/dev/null || echo "")

    if [ -z "$CLUSTER_NAME" ] || [ -z "$SERVICE_NAME" ]; then
        log_warn "ECS service not yet deployed. Skipping update."
        return
    fi

    log_info "Forcing new deployment of ECS service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --no-cli-pager > /dev/null

    log_info "ECS service update initiated!"
}

# Display outputs
display_outputs() {
    echo ""
    echo "========================================"
    echo "Frontend Deployment Complete!"
    echo "========================================"

    cd "$FRONTEND_TF_DIR"

    echo ""
    echo "CloudFront:"
    echo "  URL:    $(terraform output -raw cloudfront_url)"
    echo "  Domain: $(terraform output -raw cloudfront_domain_name)"

    echo ""
    echo "ALB:"
    echo "  DNS:    $(terraform output -raw alb_dns_name)"

    echo ""
    echo "ECS:"
    echo "  Cluster: $(terraform output -raw ecs_cluster_name)"
    echo "  Service: $(terraform output -raw ecs_service_name)"

    echo ""
    echo "ECR Repository:"
    echo "  $(terraform output -raw ecr_repository_url)"

    echo ""
    echo "Cognito:"
    echo "  User Pool ID:       $(terraform output -raw cognito_user_pool_id)"
    echo "  User Pool Client:   $(terraform output -raw cognito_user_pool_client_id)"
    echo "  Identity Pool ID:   $(terraform output -raw cognito_identity_pool_id)"
    echo "  Domain:             $(terraform output -raw cognito_domain)"

    # Save frontend config
    CONFIG_FILE="$PROJECT_ROOT/frontend-config.json"
    terraform output -json frontend_config > "$CONFIG_FILE"
    echo ""
    log_info "Frontend config saved to: $CONFIG_FILE"

    CLOUDFRONT_URL=$(terraform output -raw cloudfront_url)
    USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

    echo ""
    log_info "Frontend deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Wait 5-10 minutes for ECS tasks to start"
    echo "  2. Create Cognito users via AWS Console or CLI"
    echo "  3. Access app at: $CLOUDFRONT_URL"
    echo "  4. Or deploy tools: ./deploy-tools.sh (coming soon)"
    echo ""
    echo "Create a test user:"
    echo "  aws cognito-idp admin-create-user \\"
    echo "    --user-pool-id $USER_POOL_ID \\"
    echo "    --username test@example.com \\"
    echo "    --user-attributes Name=email,Value=test@example.com \\"
    echo "    --temporary-password 'TempPass123!' \\"
    echo "    --message-action SUPPRESS"
    echo ""
    echo "Monitor ECS logs:"
    echo "  aws logs tail /ecs/deep-research-frontend-dev --follow"
}

# Main deployment flow
main() {
    check_prerequisites
    deploy_infrastructure  # Deploy infra first to get CloudFront URL
    build_frontend         # Build with proper env vars
    build_docker_image
    update_ecs_service
    display_outputs
}

# Run main
main
