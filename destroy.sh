#!/bin/bash
set -e

# Deep Research Agent - Main Destruction Orchestrator
# Routes to specific destroy scripts

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
    echo "  Deep Research Agent - Destruction"
    echo "========================================"
    echo ""
    echo -e "${RED}⚠️  WARNING: Destructive Operation${NC}"
    echo ""
}

# Display menu
display_menu() {
    echo "What would you like to destroy?"
    echo ""
    echo "  1) Backend      (AgentCore Runtime + Infrastructure)"
    echo "  2) Frontend     (Cognito + CloudFront + ECS)"
    echo "  3) Tools        (Gateway + Lambda Services)"
    echo "  4) Full Stack   (Frontend + Backend)"
    echo "  5) Everything   (Frontend + Tools + Backend)"
    echo ""
    echo "  0) Exit"
    echo ""
    echo -e "${YELLOW}Note: Destruction order is reverse of deployment${NC}"
    echo -e "${YELLOW}      (Frontend → Tools → Backend)${NC}"
    echo ""
}

# Check if scripts exist
check_scripts() {
    local missing=0

    if [ ! -f "./terraform/destroy-backend.sh" ]; then
        log_error "terraform/destroy-backend.sh not found"
        missing=1
    fi

    if [ ! -f "./terraform/destroy-frontend.sh" ]; then
        log_error "terraform/destroy-frontend.sh not found"
        missing=1
    fi

    if [ ! -f "./terraform/destroy-tools.sh" ]; then
        log_error "terraform/destroy-tools.sh not found"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        log_error "Required destroy scripts are missing"
        exit 1
    fi

    # Make sure scripts are executable
    chmod +x ./terraform/destroy-backend.sh
    chmod +x ./terraform/destroy-frontend.sh
    chmod +x ./terraform/destroy-tools.sh
}

# Destroy backend
destroy_backend() {
    log_step "Destroying Backend..."
    echo ""
    ./terraform/destroy-backend.sh
}

# Destroy frontend
destroy_frontend() {
    log_step "Destroying Frontend..."
    echo ""
    ./terraform/destroy-frontend.sh
}

# Destroy tools
destroy_tools() {
    if [ -f "./terraform/destroy-tools.sh" ]; then
        log_step "Destroying Tools..."
        echo ""
        ./terraform/destroy-tools.sh
    else
        log_warn "terraform/destroy-tools.sh not found, skipping"
    fi
}

# Set up for destruction (skip all confirmations in child scripts)
prepare_destruction() {
    local scope="$1"
    echo ""
    echo -e "${RED}Starting destruction: $scope${NC}"
    echo -e "${YELLOW}This operation is IRREVERSIBLE!${NC}"
    echo ""

    # Export flag to skip confirmations in child scripts
    export SKIP_CONFIRM=1
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
            prepare_destruction "Backend Infrastructure"
            destroy_backend
            ;;
        2)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 2: Frontend Only"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            prepare_destruction "Frontend Infrastructure"
            destroy_frontend
            ;;
        3)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 3: Tools Only"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            prepare_destruction "Tools Infrastructure"
            destroy_tools
            ;;
        4)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 4: Full Stack (Frontend + Backend)"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            prepare_destruction "Full Stack (Frontend + Backend)"
            destroy_frontend
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            destroy_backend
            ;;
        5)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Option 5: Everything"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            prepare_destruction "ALL Infrastructure (Frontend + Tools + Backend)"
            destroy_frontend
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            destroy_tools
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            destroy_backend
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
    log_info "Destruction Complete!"
    echo "========================================"
    echo ""
    echo "All selected resources have been removed from AWS."
    echo ""
}

# Run main
main
