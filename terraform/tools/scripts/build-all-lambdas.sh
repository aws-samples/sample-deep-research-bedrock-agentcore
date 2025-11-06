#!/bin/bash

# Build all Lambda deployment packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDAS_DIR="$PROJECT_ROOT/lambdas"
BUILD_DIR="$PROJECT_ROOT/build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Building All Lambda Deployment Packages${NC}"
echo "================================================"

# Create build directory
mkdir -p "$BUILD_DIR"

# Function to build a single Lambda
build_lambda() {
    local lambda_name=$1
    local lambda_dir="$LAMBDAS_DIR/$lambda_name"
    local output_zip="$BUILD_DIR/${lambda_name}-lambda.zip"
    local temp_dir="$BUILD_DIR/${lambda_name}-temp"

    echo ""
    echo -e "${YELLOW}📦 Building $lambda_name Lambda...${NC}"
    echo "================================================"

    if [ ! -d "$lambda_dir" ]; then
        echo -e "${RED}❌ Lambda directory not found: $lambda_dir${NC}"
        return 1
    fi

    # Clean up previous build
    rm -rf "$temp_dir"
    rm -f "$output_zip"

    # Create temp directory
    mkdir -p "$temp_dir"

    echo "📥 Installing dependencies..."
    if [ -f "$lambda_dir/requirements.txt" ]; then
        # Install dependencies for Linux ARM64 platform (Lambda runtime)
        # Use Docker to build in Lambda-compatible environment

        echo "  Using Docker to build Lambda-compatible packages..."

        # Check if Docker is available
        if command -v docker &> /dev/null && docker ps &> /dev/null; then
            echo "  ✓ Docker available, using Lambda ARM64 container for build"
            # Use Amazon Linux 2023 ARM64 image (matches Lambda runtime)
            if docker run --rm \
                --platform linux/arm64 \
                --entrypoint /bin/bash \
                -v "$lambda_dir:/src:ro" \
                -v "$temp_dir:/build" \
                public.ecr.aws/lambda/python:3.13-arm64 \
                -c "pip3 install -r /src/requirements.txt -t /build --upgrade --no-cache-dir && chown -R $(id -u):$(id -g) /build"; then
                echo "  ✓ Docker build successful"
            else
                echo "  ✗ Docker build failed, falling back to local install"
                pip3 install -r "$lambda_dir/requirements.txt" -t "$temp_dir" \
                    --upgrade \
                    --no-cache-dir
            fi
        else
            echo "  ⚠️  Docker not available or not running, using local install"
            echo "     (This may cause compatibility issues on Lambda ARM64)"
            pip3 install -r "$lambda_dir/requirements.txt" -t "$temp_dir" \
                --upgrade \
                --no-cache-dir
        fi

        echo "📄 Copying Lambda function..."
        cp "$lambda_dir/lambda_function.py" "$temp_dir/"

        # Clean up unnecessary files to reduce package size
        find "$temp_dir" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
        find "$temp_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$temp_dir" -name "*.pyc" -delete 2>/dev/null || true
        find "$temp_dir" -name "*.pyo" -delete 2>/dev/null || true
    else
        # No requirements.txt, just copy the function
        echo "📄 Copying Lambda function..."
        cp "$lambda_dir/lambda_function.py" "$temp_dir/"
    fi

    echo "📦 Creating ZIP archive..."
    cd "$temp_dir"
    zip -r "$output_zip" . -q

    # Clean up temp directory
    cd "$BUILD_DIR"
    rm -rf "$temp_dir"

    # Get size in MB
    size=$(du -h "$output_zip" | cut -f1)

    echo -e "${GREEN}✅ Package created: ${lambda_name}-lambda.zip ($size)${NC}"
    echo "================================================"

    return 0
}

# Build all Lambdas
# Note: finance Lambda uses simplified version without numpy/pandas
lambdas=("tavily" "wikipedia" "duckduckgo" "google-search" "arxiv" "finance")

failed_builds=()

for lambda_name in "${lambdas[@]}"; do
    if build_lambda "$lambda_name"; then
        echo -e "${GREEN}✅ $lambda_name build successful${NC}"
    else
        echo -e "${RED}❌ $lambda_name build failed${NC}"
        failed_builds+=("$lambda_name")
    fi
done

echo ""
echo "================================================"

if [ ${#failed_builds[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All Lambda packages built successfully!${NC}"
    echo ""
    echo "Build artifacts:"
    ls -lh "$BUILD_DIR"/*.zip
    echo ""
    echo "📍 Output directory: $BUILD_DIR"
else
    echo -e "${RED}❌ Some builds failed:${NC}"
    for lambda in "${failed_builds[@]}"; do
        echo "  - $lambda"
    done
    exit 1
fi
