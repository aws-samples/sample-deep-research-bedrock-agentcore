#!/bin/bash

# Clean build - 가상환경에서 완전히 격리된 빌드
# 로컬 환경 의존성 충돌 문제 해결

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$PROJECT_ROOT/lambdas/tavily"
BUILD_DIR="$PROJECT_ROOT/build"

echo "🚀 Clean Build (Virtual Environment)"
echo "================================================"

# Clean everything
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Create temporary virtual environment
echo "📦 Creating temporary virtual environment..."
cd "$BUILD_DIR"
python3 -m venv temp_venv

# Activate and install
echo "📥 Installing dependencies in clean environment..."
source temp_venv/bin/activate

pip install --upgrade pip --quiet
pip install -r "$LAMBDA_DIR/requirements.txt" --quiet

# Create package directory
mkdir -p package
cp "$LAMBDA_DIR/lambda_function.py" package/

# Copy only site-packages (not venv metadata)
echo "📦 Copying installed packages..."
cp -r temp_venv/lib/python*/site-packages/* package/ 2>/dev/null || true

# Deactivate venv
deactivate

# Clean up
echo "🧹 Cleaning up..."
cd package

# Remove venv-related files
rm -rf pip* setuptools* wheel* pkg_resources* easy_install* 2>/dev/null || true

# Remove test files
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove boto3/botocore (Lambda runtime provides these)
rm -rf boto3* botocore* s3transfer* jmespath* 2>/dev/null || true

# Create ZIP
echo "📦 Creating ZIP archive..."
zip -r ../tavily-lambda.zip . -q

cd "$BUILD_DIR"
rm -rf package temp_venv

# Check size
SIZE=$(wc -c < tavily-lambda.zip)
SIZE_MB=$((SIZE / 1024 / 1024))
echo "✅ Package created: tavily-lambda.zip (${SIZE_MB}MB)"

if [ $SIZE_MB -gt 50 ]; then
    echo "❌ Error: Package exceeds 50MB limit"
    exit 1
fi

echo "================================================"
echo "✅ Clean build complete!"
echo "📍 Output: $BUILD_DIR/tavily-lambda.zip"
