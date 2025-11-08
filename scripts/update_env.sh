#!/bin/bash

# Update .env file with Terraform outputs
# This script reads Terraform outputs and updates AWS resource values in .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

echo "📝 Updating .env file with Terraform outputs..."

# Check if terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

# Get Terraform outputs
cd "$TERRAFORM_DIR"

# Check if Terraform state exists
if [ ! -f "terraform.tfstate" ]; then
    echo "❌ Terraform state not found. Run 'terraform apply' first."
    exit 1
fi

# Extract outputs
DYNAMODB_TABLE=$(terraform output -raw dynamodb_status_table 2>/dev/null || echo "")
S3_BUCKET=$(terraform output -raw s3_outputs_bucket 2>/dev/null || echo "")
AGENTCORE_MEMORY_ID=$(terraform output -raw agentcore_memory_id 2>/dev/null || echo "")
AWS_REGION=$(terraform output -json | jq -r '.summary.value.region' 2>/dev/null || echo "us-west-2")

if [ -z "$DYNAMODB_TABLE" ] || [ -z "$S3_BUCKET" ] || [ -z "$AGENTCORE_MEMORY_ID" ]; then
    echo "❌ Failed to get Terraform outputs"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo "📄 Creating new .env file..."
    cat > "$ENV_FILE" << EOF
# AWS Configuration
AWS_REGION=$AWS_REGION

# AWS Resources (from Terraform)
DYNAMODB_STATUS_TABLE=$DYNAMODB_TABLE
S3_OUTPUTS_BUCKET=$S3_BUCKET
AGENTCORE_MEMORY_ID=$AGENTCORE_MEMORY_ID

# LangSmith Configuration (Optional)
LANGCHAIN_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=research-agent

# Tavily AI Search API Key
TAVILY_API_KEY=

# Google Custom Search API
GOOGLE_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=
EOF
    echo "✅ Created .env file"
else
    # Update existing .env file
    echo "🔄 Updating existing .env file..."

    # Create temp file
    TEMP_FILE=$(mktemp)

    # Read .env and update AWS resource values
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip AWS Resources section marker
        if [[ "$line" == "# AWS Resources (from Terraform)" ]]; then
            echo "$line" >> "$TEMP_FILE"
            continue
        fi

        # Update AWS resource variables
        if [[ "$line" =~ ^DYNAMODB_STATUS_TABLE= ]]; then
            echo "DYNAMODB_STATUS_TABLE=$DYNAMODB_TABLE" >> "$TEMP_FILE"
        elif [[ "$line" =~ ^S3_OUTPUTS_BUCKET= ]]; then
            echo "S3_OUTPUTS_BUCKET=$S3_BUCKET" >> "$TEMP_FILE"
        elif [[ "$line" =~ ^AGENTCORE_MEMORY_ID= ]]; then
            echo "AGENTCORE_MEMORY_ID=$AGENTCORE_MEMORY_ID" >> "$TEMP_FILE"
        elif [[ "$line" =~ ^AWS_REGION= ]]; then
            echo "AWS_REGION=$AWS_REGION" >> "$TEMP_FILE"
        else
            echo "$line" >> "$TEMP_FILE"
        fi
    done < "$ENV_FILE"

    # Check if AWS Resources section exists
    if ! grep -q "DYNAMODB_STATUS_TABLE=" "$TEMP_FILE"; then
        # Add AWS Resources section after AWS_REGION
        sed -i.bak "/^AWS_REGION=/a\\
\\
# AWS Resources (from Terraform)\\
DYNAMODB_STATUS_TABLE=$DYNAMODB_TABLE\\
S3_OUTPUTS_BUCKET=$S3_BUCKET\\
AGENTCORE_MEMORY_ID=$AGENTCORE_MEMORY_ID
" "$TEMP_FILE"
        rm "${TEMP_FILE}.bak"
    fi

    # Replace original file
    mv "$TEMP_FILE" "$ENV_FILE"
    echo "✅ Updated .env file"
fi

echo ""
echo "📊 AWS Resources:"
echo "   AWS Region: $AWS_REGION"
echo "   DynamoDB Table: $DYNAMODB_TABLE"
echo "   S3 Bucket: $S3_BUCKET"
echo "   Memory ID: $AGENTCORE_MEMORY_ID"
echo ""
echo "✅ Done! .env file is up to date."
