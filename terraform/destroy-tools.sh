#!/bin/bash
set -e

# Deep Research Agent - Tools Destroy Script
# Destroys: Gateway + Lambda Tools + Additional Services

echo "========================================"
echo "Deep Research Agent - Tools Destroy"
echo "========================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TOOLS_SCRIPT_DIR="${SCRIPT_DIR}/tools/scripts"
TOOLS_DESTROY_SCRIPT="${TOOLS_SCRIPT_DIR}/destroy.sh"

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

# Check if tools destroy script exists
check_tools_exists() {
    if [ ! -f "$TOOLS_DESTROY_SCRIPT" ]; then
        log_error "Tools destroy script not found at $TOOLS_DESTROY_SCRIPT"
        exit 1
    fi

    # Make sure it's executable
    chmod +x "$TOOLS_DESTROY_SCRIPT"

    log_info "Tools destroy script found"
}

# Execute tools destroy script
destroy_tools() {
    echo ""
    log_info "Executing tools destroy script..."
    echo ""

    "$TOOLS_DESTROY_SCRIPT"
}

# Display completion message
display_completion() {
    echo ""
    echo "========================================"
    log_info "Tools Destruction Complete!"
    echo "========================================"
    echo ""
}

# Main destruction flow
main() {
    check_tools_exists
    destroy_tools
    display_completion
}

# Run main
main
