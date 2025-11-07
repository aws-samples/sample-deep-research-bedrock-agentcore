# ============================================================================
# AWS Systems Manager Parameter Store - Configuration Management
# ============================================================================
# Stores runtime configuration values that the Agent needs to access
# These are NOT secrets - use Secrets Manager for sensitive data

# AgentCore Memory ID from parent deployment
resource "aws_ssm_parameter" "agentcore_memory_id" {
  name        = "/${var.project_name}/${local.suffix}/agentcore/memory-id"
  description = "AgentCore Memory ID for research agent"
  type        = "String"
  value       = var.agentcore_memory_id

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-memory-id-${local.suffix}"
    }
  )
}

# DynamoDB Status Table from parent deployment
resource "aws_ssm_parameter" "dynamodb_status_table" {
  name        = "/${var.project_name}/${local.suffix}/dynamodb/status-table"
  description = "DynamoDB table name for research status tracking"
  type        = "String"
  value       = var.dynamodb_status_table

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-dynamodb-status-${local.suffix}"
    }
  )
}

# S3 Outputs Bucket from parent deployment
resource "aws_ssm_parameter" "s3_outputs_bucket" {
  name        = "/${var.project_name}/${local.suffix}/s3/outputs-bucket"
  description = "S3 bucket name for research outputs"
  type        = "String"
  value       = var.s3_outputs_bucket

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-s3-outputs-${local.suffix}"
    }
  )
}

# AWS Region
resource "aws_ssm_parameter" "aws_region" {
  name        = "/${var.project_name}/${local.suffix}/config/region"
  description = "AWS region for deployment"
  type        = "String"
  value       = var.aws_region

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-region-${local.suffix}"
    }
  )
}

# Gateway URL (generated after deployment)
resource "aws_ssm_parameter" "gateway_url" {
  name        = "/${var.project_name}/${local.suffix}/gateway/url"
  description = "AgentCore Gateway URL for MCP client access"
  type        = "String"
  value       = aws_bedrockagentcore_gateway.research_gateway.gateway_url

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-gateway-url-${local.suffix}"
    }
  )

  depends_on = [aws_bedrockagentcore_gateway.research_gateway]
}

# Gateway ARN (generated after deployment)
resource "aws_ssm_parameter" "gateway_arn" {
  name        = "/${var.project_name}/${local.suffix}/gateway/arn"
  description = "AgentCore Gateway ARN for IAM policies"
  type        = "String"
  value       = aws_bedrockagentcore_gateway.research_gateway.gateway_arn

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-gateway-arn-${local.suffix}"
    }
  )

  depends_on = [aws_bedrockagentcore_gateway.research_gateway]
}

# Gateway ID (generated after deployment)
resource "aws_ssm_parameter" "gateway_id" {
  name        = "/${var.project_name}/${local.suffix}/gateway/id"
  description = "AgentCore Gateway ID"
  type        = "String"
  value       = aws_bedrockagentcore_gateway.research_gateway.gateway_id

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-gateway-id-${local.suffix}"
    }
  )

  depends_on = [aws_bedrockagentcore_gateway.research_gateway]
}

# ============================================================================
# Backend-compatible Gateway Parameters (for Agent Runtime discovery)
# ============================================================================
# These parameters use a fixed path that Backend can discover without knowing suffix
# Path format: /{project_name}/tools/gateway/url

resource "aws_ssm_parameter" "gateway_url_backend_compat" {
  name        = "/${var.project_name}/tools/gateway/url"
  description = "Gateway URL for Agent Runtime (backend-compatible path)"
  type        = "String"
  value       = aws_bedrockagentcore_gateway.research_gateway.gateway_url

  tags = merge(
    local.common_tags,
    {
      Name    = "${var.project_name}-gateway-url-backend-compat"
      Purpose = "Backend Runtime Integration"
    }
  )

  depends_on = [aws_bedrockagentcore_gateway.research_gateway]
}

resource "aws_ssm_parameter" "gateway_region_backend_compat" {
  name        = "/${var.project_name}/tools/config/region"
  description = "Gateway region for Agent Runtime (backend-compatible path)"
  type        = "String"
  value       = data.aws_region.current.id

  tags = merge(
    local.common_tags,
    {
      Name    = "${var.project_name}-gateway-region-backend-compat"
      Purpose = "Backend Runtime Integration"
    }
  )
}

# ============================================================================
# Optional: LangSmith Configuration in Secrets Manager
# ============================================================================
# Only created if langchain_api_key is provided

resource "aws_secretsmanager_secret" "langchain_api_key" {
  count = var.langchain_api_key != "" ? 1 : 0

  name        = "${var.project_name}-langchain-api-key-${local.suffix}"
  description = "LangSmith API Key for tracing and monitoring"

  # Force overwrite if secret is scheduled for deletion
  force_overwrite_replica_secret = true

  # Set to 0 to immediately delete when terraform destroy is called
  recovery_window_in_days = 0

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-langchain-api-key-${local.suffix}"
    }
  )
}

resource "aws_secretsmanager_secret_version" "langchain_api_key" {
  count = var.langchain_api_key != "" ? 1 : 0

  secret_id = aws_secretsmanager_secret.langchain_api_key[0].id
  secret_string = jsonencode({
    api_key = var.langchain_api_key
  })
}

# Store LangSmith project name in Parameter Store
resource "aws_ssm_parameter" "langchain_project" {
  count = var.langchain_project != "" ? 1 : 0

  name        = "/${var.project_name}/${local.suffix}/langchain/project"
  description = "LangSmith project name for tracing"
  type        = "String"
  value       = var.langchain_project

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-langchain-project-${local.suffix}"
    }
  )
}

# Store LangSmith tracing flag in Parameter Store
resource "aws_ssm_parameter" "langchain_tracing" {
  count = var.langchain_tracing_v2 != "" ? 1 : 0

  name        = "/${var.project_name}/${local.suffix}/langchain/tracing-v2"
  description = "Enable LangSmith tracing V2"
  type        = "String"
  value       = var.langchain_tracing_v2

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-langchain-tracing-${local.suffix}"
    }
  )
}
