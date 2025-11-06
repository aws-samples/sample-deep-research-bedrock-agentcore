#!/bin/bash
set -e

# Deep Research Agent - Main Deployment Orchestrator
# Routes to specific deployment scripts

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}▶${NC} $1"
}

# Display banner
display_banner() {
    echo "========================================"
    echo "  Deep Research Agent - Deployment"
    echo "========================================"
    echo ""
}

# Display menu
display_menu() {
    echo "What would you like to deploy?"
    echo ""
    echo "  1) Backend      (AgentCore Runtime + Infrastructure)"
    echo "  2) Frontend     (Cognito + Amplify/ECS + BFF)"
    echo "  3) Tools        (Gateway + Additional Services)"
    echo "  4) Full Stack   (Backend + Frontend)"
    echo "  5) Everything   (Backend + Frontend + Tools)"
    echo ""
    echo "  0) Exit"
    echo ""
}

# Check if scripts exist
check_scripts() {
    local missing=0

    if [ ! -f "./terraform/deploy-backend.sh" ]; then
        log_error "terraform/deploy-backend.sh not found"
        missing=1
    fi

    if [ ! -f "./terraform/deploy-frontend.sh" ]; then
        log_error "terraform/deploy-frontend.sh not found"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        log_error "Required deployment scripts are missing"
        exit 1
    fi

    # Make sure scripts are executable
    chmod +x ./terraform/deploy-backend.sh
    chmod +x ./terraform/deploy-frontend.sh
    chmod +x ./terraform/deploy-tools.sh
}

# Deploy backend
deploy_backend() {
    log_step "Deploying Backend..."
    echo ""
    ./terraform/deploy-backend.sh
}

# Deploy frontend
deploy_frontend() {
    log_step "Deploying Frontend..."
    echo ""
    ./terraform/deploy-frontend.sh
}

# Deploy tools
deploy_tools() {
    if [ -f "./terraform/deploy-tools.sh" ]; then
        log_step "Deploying Tools..."
        echo ""
        ./terraform/deploy-tools.sh
    else
        log_warn "terraform/deploy-tools.sh not yet implemented"
        echo ""
        echo "Coming soon: Gateway, Lambda Tools, etc."
    fi
}

# Main function
main() {
    display_banner
    check_scripts
    display_menu

    read -p "Select option (0-5): " OPTION
    echo ""

    case $OPTION in
        1)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 1: Backend Only"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_backend
            ;;
        2)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 2: Frontend Only"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_frontend
            ;;
        3)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 3: Tools Only"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_tools
            ;;
        4)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 4: Full Stack (Backend + Frontend)"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_backend
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_frontend
            ;;
        5)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 5: Everything"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_backend
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_frontend
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            deploy_tools
            ;;
        0)
            log_info "Exiting..."
            exit 0
            ;;
        *)
            log_error "Invalid option. Please select 0-5."
            exit 1
            ;;
    esac

    echo ""
    echo "========================================"
    log_info "Deployment Complete!"
    echo "========================================"
}

# Run main
main
