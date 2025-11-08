#!/bin/bash

# Show Deployment Outputs
# Displays all key ARNs, IDs, and URLs from deployed infrastructure

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "========================================"
echo "  Deployment Outputs"
echo "========================================"
echo ""

# Function to print section header
print_section() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to print key-value pair
print_kv() {
    printf "${GREEN}%-30s${NC} %s\n" "$1:" "$2"
}

# Check Backend outputs
print_section "Backend Infrastructure"

BACKEND_DIR="$PROJECT_ROOT/terraform/backend"
if [ -f "$BACKEND_DIR/terraform.tfstate" ]; then
    cd "$BACKEND_DIR"

    REGION=$(terraform output -raw aws_region 2>/dev/null || echo "N/A")
    MEMORY_ID=$(terraform output -raw agentcore_memory_id 2>/dev/null || echo "N/A")
    CHAT_MEMORY_ID=$(terraform output -raw chat_memory_id 2>/dev/null || echo "N/A")
    STATUS_TABLE=$(terraform output -raw dynamodb_status_table 2>/dev/null || echo "N/A")
    USER_PREFS_TABLE=$(terraform output -raw dynamodb_user_preferences_table 2>/dev/null || echo "N/A")
    S3_BUCKET=$(terraform output -raw s3_outputs_bucket 2>/dev/null || echo "N/A")
    RESEARCH_RUNTIME_ID=$(terraform output -raw agent_runtime_id 2>/dev/null || echo "N/A")
    CHAT_RUNTIME_ID=$(terraform output -raw chat_agent_runtime_id 2>/dev/null || echo "N/A")

    print_kv "AWS Region" "$REGION"
    print_kv "Research Memory ID" "$MEMORY_ID"
    print_kv "Chat Memory ID" "$CHAT_MEMORY_ID"
    print_kv "Research Runtime ID" "$RESEARCH_RUNTIME_ID"
    print_kv "Chat Runtime ID" "$CHAT_RUNTIME_ID"
    print_kv "Status Table" "$STATUS_TABLE"
    print_kv "User Preferences Table" "$USER_PREFS_TABLE"
    print_kv "S3 Outputs Bucket" "$S3_BUCKET"
else
    echo -e "${YELLOW}Backend not deployed${NC}"
fi

echo ""

# Check Frontend outputs
print_section "Frontend Infrastructure"

FRONTEND_DIR="$PROJECT_ROOT/terraform/frontend"
if [ -f "$FRONTEND_DIR/terraform.tfstate" ]; then
    cd "$FRONTEND_DIR"

    CLOUDFRONT_URL=$(terraform output -raw cloudfront_url 2>/dev/null || echo "N/A")
    CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain_name 2>/dev/null || echo "N/A")
    ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "N/A")
    USER_POOL_ID=$(terraform output -raw cognito_user_pool_id 2>/dev/null || echo "N/A")
    CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id 2>/dev/null || echo "N/A")
    IDENTITY_POOL_ID=$(terraform output -raw cognito_identity_pool_id 2>/dev/null || echo "N/A")

    print_kv "CloudFront URL" "$CLOUDFRONT_URL"
    print_kv "CloudFront Domain" "$CLOUDFRONT_DOMAIN"
    print_kv "ALB DNS" "$ALB_DNS"
    print_kv "Cognito User Pool ID" "$USER_POOL_ID"
    print_kv "Cognito Client ID" "$CLIENT_ID"
    print_kv "Cognito Identity Pool ID" "$IDENTITY_POOL_ID"
else
    echo -e "${YELLOW}Frontend not deployed${NC}"
fi

echo ""

# Check Tools/Gateway outputs
print_section "Tools & Gateway"

TOOLS_DIR="$PROJECT_ROOT/terraform/tools/terraform"
if [ -f "$TOOLS_DIR/terraform.tfstate" ]; then
    cd "$TOOLS_DIR"

    GATEWAY_ID=$(terraform output -raw gateway_id 2>/dev/null || echo "N/A")
    GATEWAY_URL=$(terraform output -raw gateway_url 2>/dev/null || echo "N/A")

    print_kv "Gateway ID" "$GATEWAY_ID"
    print_kv "Gateway URL" "$GATEWAY_URL"
else
    echo -e "${YELLOW}Tools not deployed${NC}"
fi

echo ""

# Check for frontend-config.json
print_section "Configuration Files"

if [ -f "$PROJECT_ROOT/frontend-config.json" ]; then
    print_kv "Frontend Config" "$PROJECT_ROOT/frontend-config.json"
else
    echo -e "${YELLOW}frontend-config.json not found${NC}"
fi

if [ -f "$PROJECT_ROOT/.env" ]; then
    print_kv "Environment File" "$PROJECT_ROOT/.env"
else
    echo -e "${YELLOW}.env not found${NC}"
fi

echo ""
echo "========================================"
echo ""

# Show quick actions
echo -e "${CYAN}Quick Actions:${NC}"
echo ""
if [ "$CLOUDFRONT_URL" != "N/A" ]; then
    echo "  • Open application:"
    echo "    $CLOUDFRONT_URL"
    echo ""
fi

if [ "$USER_POOL_ID" != "N/A" ]; then
    echo "  • Create user:"
    echo "    aws cognito-idp admin-create-user \\"
    echo "      --user-pool-id $USER_POOL_ID \\"
    echo "      --username user@example.com \\"
    echo "      --user-attributes Name=email,Value=user@example.com \\"
    echo "      --temporary-password 'TempPass123!' \\"
    echo "      --message-action SUPPRESS"
    echo ""
fi

echo "  • View configuration:"
echo "    cat $PROJECT_ROOT/.env"
echo ""
echo "  • View frontend config:"
echo "    cat $PROJECT_ROOT/frontend-config.json"
echo ""
