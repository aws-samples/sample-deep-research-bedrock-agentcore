#!/usr/bin/env python3
"""Update .env file with Terraform outputs

This script automatically updates AWS resource values in .env file
from Terraform outputs after deployment.

Usage:
    python scripts/update_env.py
    # or
    ./scripts/update_env.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path


def get_terraform_outputs():
    """Get Terraform outputs as JSON"""
    script_dir = Path(__file__).parent
    terraform_backend_dir = script_dir.parent / "terraform" / "backend"

    if not terraform_backend_dir.exists():
        print(f"❌ Terraform backend directory not found: {terraform_backend_dir}")
        sys.exit(1)

    # Check if terraform state exists
    if not (terraform_backend_dir / "terraform.tfstate").exists():
        print("❌ Terraform state not found. Run './deploy.sh' first.")
        sys.exit(1)

    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=terraform_backend_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get Terraform outputs: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse Terraform outputs: {e}")
        sys.exit(1)


def update_env_file(outputs):
    """Update .env file with Terraform outputs"""
    script_dir = Path(__file__).parent
    env_file = script_dir.parent / ".env"

    # Extract values from outputs
    dynamodb_status_table = outputs.get("dynamodb_status_table", {}).get("value", "")
    dynamodb_user_prefs_table = outputs.get("dynamodb_user_preferences_table", {}).get("value", "")
    s3_bucket = outputs.get("s3_outputs_bucket", {}).get("value", "")
    memory_id = outputs.get("agentcore_memory_id", {}).get("value", "")
    chat_memory_id = outputs.get("chat_memory_id", {}).get("value", "")
    aws_region = outputs.get("summary", {}).get("value", {}).get("region", "us-west-2")

    if not dynamodb_status_table or not s3_bucket or not memory_id:
        print("❌ Failed to extract required Terraform outputs")
        sys.exit(1)

    print(f"📊 AWS Resources:")
    print(f"   AWS Region: {aws_region}")
    print(f"   DynamoDB Status Table: {dynamodb_status_table}")
    print(f"   DynamoDB User Preferences Table: {dynamodb_user_prefs_table}")
    print(f"   S3 Bucket: {s3_bucket}")
    print(f"   Research Memory ID: {memory_id}")
    print(f"   Chat Memory ID: {chat_memory_id}")
    print()

    # Create .env file if it doesn't exist
    if not env_file.exists():
        print("📄 .env file not found - please copy from .env.example first")
        sys.exit(1)

    # Update existing .env file
    print("🔄 Updating existing .env file...")

    lines = env_file.read_text().splitlines()
    updated_lines = []

    for line in lines:
        # Update AWS resource variables to match .env.example structure
        if line.startswith("AGENTCORE_MEMORY_ID="):
            updated_lines.append(f"AGENTCORE_MEMORY_ID={memory_id}")
        elif line.startswith("DYNAMODB_STATUS_TABLE="):
            updated_lines.append(f"DYNAMODB_STATUS_TABLE={dynamodb_status_table}")
        elif line.startswith("DYNAMODB_USER_PREFERENCES_TABLE="):
            updated_lines.append(f"DYNAMODB_USER_PREFERENCES_TABLE={dynamodb_user_prefs_table}")
        elif line.startswith("S3_OUTPUTS_BUCKET="):
            updated_lines.append(f"S3_OUTPUTS_BUCKET={s3_bucket}")
        elif line.startswith("CHAT_AGENT_MEMORY_ID="):
            updated_lines.append(f"CHAT_AGENT_MEMORY_ID={chat_memory_id}")
        elif line.startswith("AWS_REGION="):
            # Keep existing region (don't overwrite)
            updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Write updated content
    env_file.write_text("\n".join(updated_lines) + "\n")
    print("✅ Updated .env file")


def main():
    print("📝 Updating .env file with Terraform outputs...")
    print()

    outputs = get_terraform_outputs()
    update_env_file(outputs)

    print()
    print("✅ Done! .env file is up to date.")


if __name__ == "__main__":
    main()
