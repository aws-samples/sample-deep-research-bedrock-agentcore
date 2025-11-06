# SSM Parameter Store for runtime configuration
# BFF reads these parameters to get AgentCore Runtime information

# Research Agent Runtime
resource "aws_ssm_parameter" "agentcore_runtime_arn" {
  name        = "/${local.project_name}/${var.environment}/agentcore/runtime-arn"
  description = "Research Agent Runtime ARN"
  type        = "String"
  value       = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_arn

  tags = local.common_tags
}

resource "aws_ssm_parameter" "agentcore_runtime_id" {
  name        = "/${local.project_name}/${var.environment}/agentcore/runtime-id"
  description = "Research Agent Runtime ID"
  type        = "String"
  value       = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_id

  tags = local.common_tags
}

# Chat Agent Runtime
resource "aws_ssm_parameter" "chat_runtime_arn" {
  name        = "/${local.project_name}/${var.environment}/agentcore/chat-runtime-arn"
  description = "Chat Agent Runtime ARN"
  type        = "String"
  value       = awscc_bedrockagentcore_runtime.chat_agent.agent_runtime_arn

  tags = local.common_tags
}

resource "aws_ssm_parameter" "chat_runtime_id" {
  name        = "/${local.project_name}/${var.environment}/agentcore/chat-runtime-id"
  description = "Chat Agent Runtime ID"
  type        = "String"
  value       = awscc_bedrockagentcore_runtime.chat_agent.agent_runtime_id

  tags = local.common_tags
}

resource "aws_ssm_parameter" "dynamodb_status_table" {
  name        = "/${local.project_name}/${var.environment}/dynamodb/status-table"
  description = "DynamoDB Status Table Name"
  type        = "String"
  value       = aws_dynamodb_table.research_status.name

  tags = local.common_tags
}

resource "aws_ssm_parameter" "dynamodb_user_preferences_table" {
  name        = "/${local.project_name}/${var.environment}/dynamodb/user-preferences-table"
  description = "DynamoDB User Preferences Table Name"
  type        = "String"
  value       = aws_dynamodb_table.user_preferences.name

  tags = local.common_tags
}

resource "aws_ssm_parameter" "s3_outputs_bucket" {
  name        = "/${local.project_name}/${var.environment}/s3/outputs-bucket"
  description = "S3 Outputs Bucket Name"
  type        = "String"
  value       = aws_s3_bucket.research_outputs.bucket

  tags = local.common_tags
}

resource "aws_ssm_parameter" "agentcore_memory_id" {
  name        = "/${local.project_name}/${var.environment}/agentcore/memory-id"
  description = "AgentCore Memory ID for Research Agent (LTM with Semantic Search)"
  type        = "String"
  value       = aws_bedrockagentcore_memory.research_memory.id

  tags = local.common_tags
}

resource "aws_ssm_parameter" "chat_memory_id" {
  name        = "/${local.project_name}/${var.environment}/agentcore/chat-memory-id"
  description = "AgentCore Memory ID for Chat Agent (STM only)"
  type        = "String"
  value       = aws_bedrockagentcore_memory.chat_memory.id

  tags = local.common_tags
}

output "ssm_parameters" {
  description = "SSM Parameter Store paths for BFF configuration"
  value = {
    research_runtime_arn = aws_ssm_parameter.agentcore_runtime_arn.name
    research_runtime_id  = aws_ssm_parameter.agentcore_runtime_id.name
    chat_runtime_arn     = aws_ssm_parameter.chat_runtime_arn.name
    chat_runtime_id      = aws_ssm_parameter.chat_runtime_id.name
    status_table         = aws_ssm_parameter.dynamodb_status_table.name
    outputs_bucket       = aws_ssm_parameter.s3_outputs_bucket.name
    research_memory_id   = aws_ssm_parameter.agentcore_memory_id.name
    chat_memory_id       = aws_ssm_parameter.chat_memory_id.name
  }
}
