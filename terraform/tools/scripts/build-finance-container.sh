#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FINANCE_DIR="$PROJECT_ROOT/lambdas/finance"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 Building Finance Lambda Container Image${NC}"
echo "================================================"

# Get AWS account and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
# Use environment variable AWS_REGION if set, otherwise fall back to AWS CLI config
REGION=${AWS_REGION:-$(aws configure get region || echo "us-west-2")}

ECR_REPO_NAME="research-tools-finance-lambda"
IMAGE_TAG="latest"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $REGION"
echo "ECR Repository: $ECR_REPO_NAME"

# Create ECR repository if it doesn't exist
echo ""
echo -e "${YELLOW}📦 Creating ECR repository (if not exists)...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION

# Login to ECR
echo ""
echo -e "${YELLOW}🔐 Logging in to ECR...${NC}"
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Build Docker image
echo ""
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
cd $FINANCE_DIR

# Build for ARM64 platform (Lambda ARM64 runtime)
# Remove any existing builder to ensure clean state
docker buildx rm lambda-builder 2>/dev/null || true

# Use docker buildx with explicit settings for Lambda ARM64 compatibility
docker buildx create --name lambda-builder --driver docker-container --use
docker buildx build \
    --platform linux/arm64 \
    --output type=image,push=true \
    --provenance=false \
    --sbom=false \
    -t ${ECR_URI}:${IMAGE_TAG} \
    .

echo ""
echo -e "${GREEN}✅ Image built and pushed to ECR${NC}"

echo ""
echo -e "${GREEN}✅ Finance Lambda container image built and pushed!${NC}"
echo ""
echo "Image URI: ${ECR_URI}:${IMAGE_TAG}"
echo ""
echo "Next: Update Terraform to use container image"
