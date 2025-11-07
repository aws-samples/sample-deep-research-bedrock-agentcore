# AgentCore Code Interpreter
resource "aws_bedrockagentcore_code_interpreter" "research_code_interpreter" {
  name        = "deep_research_code_interpreter_${local.suffix}"
  description = "Code interpreter for chart generation and data analysis"

  network_configuration {
    network_mode = "PUBLIC"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "deep_research_code_interpreter_${local.suffix}"
    }
  )
}

# AgentCore Memory
resource "aws_bedrockagentcore_memory" "research_memory" {
  name                  = "deep_research_memory_${local.suffix}"
  description           = "Long-term memory for Deep Research Agent with semantic search"
  event_expiry_duration = 180  # 6 months in days

  tags = merge(
    local.common_tags,
    {
      Name = "deep_research_memory_${local.suffix}"
    }
  )
}

# Semantic Search Strategy for Long-term Memory
resource "aws_bedrockagentcore_memory_strategy" "semantic" {
  name        = "semantic_search_strategy_${local.suffix}"
  memory_id   = aws_bedrockagentcore_memory.research_memory.id
  type        = "SEMANTIC"
  description = "Semantic understanding and search for research agent memory"
  namespaces  = ["default"]  # SEMANTIC strategy supports only one namespace
}

# AgentCore Runtime for Research Agent
resource "awscc_bedrockagentcore_runtime" "research_agent" {
  agent_runtime_name = "deep_research_agent_runtime_${local.suffix}"
  description        = "Deep Research Agent - Dimensional research workflow with LangGraph (Build: ${null_resource.build_research_agent.id})"
  role_arn           = awscc_iam_role.agent_runtime_role.arn

  agent_runtime_artifact = {
    container_configuration = {
      container_uri = "${aws_ecr_repository.research_agent.repository_url}:latest"
    }
  }

  network_configuration = {
    network_mode = "PUBLIC"
  }

  environment_variables = {
    # AWS Configuration
    AWS_REGION = var.aws_region
    PROJECT_NAME = var.project_name

    # DynamoDB Tables
    DYNAMODB_STATUS_TABLE = aws_dynamodb_table.research_status.name

    # S3 Outputs
    S3_OUTPUTS_BUCKET = aws_s3_bucket.research_outputs.bucket

    # AgentCore Memory
    AGENTCORE_MEMORY_ID = aws_bedrockagentcore_memory.research_memory.id

    # Application Configuration
    LOG_LEVEL = var.log_level
    ENABLE_XRAY = tostring(var.enable_xray)

    # Tool API Keys (temporary - move to Secrets Manager later)
    TAVILY_API_KEY = var.tavily_api_key
    GOOGLE_API_KEY = var.google_api_key
    GOOGLE_SEARCH_ENGINE_ID = var.google_search_engine_id

    # LangSmith Tracing
    LANGCHAIN_TRACING_V2 = var.langchain_tracing_enabled
    LANGCHAIN_PROJECT = var.langchain_project
    LANGCHAIN_API_KEY = var.langchain_api_key

    # Force update trigger when image changes
    IMAGE_BUILD_ID = null_resource.build_research_agent.id
  }

  tags = {
    Project     = local.common_tags.Project
    Environment = local.common_tags.Environment
    ManagedBy   = local.common_tags.ManagedBy
  }

  # Ensure dependencies are created first
  depends_on = [
    awscc_iam_role_policy.agent_runtime_policy,
    aws_dynamodb_table.research_status,
    aws_s3_bucket.research_outputs,
    aws_bedrockagentcore_memory.research_memory,  # Wait for memory
    aws_bedrockagentcore_memory_strategy.semantic,  # Wait for strategy
    null_resource.build_research_agent  # Wait for Docker image
  ]
}

output "agent_runtime_id" {
  description = "AgentCore Runtime ID"
  value       = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_id
}

output "agent_runtime_arn" {
  description = "AgentCore Runtime ARN"
  value       = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_arn
}

output "agent_runtime_version" {
  description = "AgentCore Runtime Version"
  value       = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_version
}

output "agent_runtime_status" {
  description = "AgentCore Runtime Status"
  value       = awscc_bedrockagentcore_runtime.research_agent.status
}

output "workload_identity_arn" {
  description = "Workload Identity ARN"
  value       = awscc_bedrockagentcore_runtime.research_agent.workload_identity_details.workload_identity_arn
}

output "agentcore_memory_id" {
  description = "AgentCore Memory ID"
  value       = aws_bedrockagentcore_memory.research_memory.id
}

output "agentcore_memory_arn" {
  description = "AgentCore Memory ARN"
  value       = aws_bedrockagentcore_memory.research_memory.arn
}

output "code_interpreter_id" {
  description = "Code Interpreter ID"
  value       = aws_bedrockagentcore_code_interpreter.research_code_interpreter.code_interpreter_id
}

output "code_interpreter_arn" {
  description = "Code Interpreter ARN"
  value       = aws_bedrockagentcore_code_interpreter.research_code_interpreter.code_interpreter_arn
}

# =============================================================================
# Chat Agent Resources
# =============================================================================

# AgentCore Memory for Chat (STM only - no strategy needed)
# STM is built-in functionality, only LTM requires strategies (SEMANTIC, SUMMARIZATION, USER_PREFERENCE)
resource "aws_bedrockagentcore_memory" "chat_memory" {
  name                  = "deep_research_chat_memory_${local.suffix}"
  description           = "Conversation memory for Research Chat - STM for session continuity"
  event_expiry_duration = 90  # 3 months in days

  tags = merge(
    local.common_tags,
    {
      Name = "deep_research_chat_memory_${local.suffix}"
      Purpose = "chat"
      MemoryType = "STM"
    }
  )
}

# AgentCore Runtime for Chat Agent
resource "awscc_bedrockagentcore_runtime" "chat_agent" {
  agent_runtime_name = "deep_research_chat_agent_runtime_${local.suffix}"
  description        = "Chat Agent for Research Q&A - Strands-based conversational interface (Build: ${null_resource.build_chat_agent.id})"
  role_arn           = awscc_iam_role.agent_runtime_role.arn

  agent_runtime_artifact = {
    container_configuration = {
      container_uri = "${aws_ecr_repository.chat_agent.repository_url}:latest"
    }
  }

  network_configuration = {
    network_mode = "PUBLIC"
  }

  environment_variables = {
    # AWS Configuration
    AWS_REGION = var.aws_region
    PROJECT_NAME = local.project_name

    # DynamoDB Tables
    DYNAMODB_STATUS_TABLE = aws_dynamodb_table.research_status.name

    # S3 Outputs
    S3_OUTPUTS_BUCKET = aws_s3_bucket.research_outputs.bucket

    # AgentCore Memory for Chat (STM only)
    AGENTCORE_MEMORY_ID = aws_bedrockagentcore_memory.chat_memory.id

    # Research Memory for accessing research findings (LTM)
    AGENTCORE_RESEARCH_MEMORY_ID = aws_bedrockagentcore_memory.research_memory.id

    # Application Configuration
    LOG_LEVEL = var.log_level
    ENABLE_XRAY = tostring(var.enable_xray)

    # Force update trigger when image changes
    IMAGE_BUILD_ID = null_resource.build_chat_agent.id
  }

  tags = {
    Project     = local.common_tags.Project
    Environment = local.common_tags.Environment
    ManagedBy   = local.common_tags.ManagedBy
    AgentType   = "chat"
  }

  # Ensure dependencies are created first
  depends_on = [
    awscc_iam_role_policy.agent_runtime_policy,
    aws_dynamodb_table.research_status,
    aws_s3_bucket.research_outputs,
    aws_bedrockagentcore_memory.chat_memory,
    null_resource.build_chat_agent  # Wait for Docker image
  ]
}

# Outputs for Chat Agent
output "chat_agent_runtime_id" {
  description = "Chat Agent Runtime ID"
  value       = awscc_bedrockagentcore_runtime.chat_agent.agent_runtime_id
}

output "chat_agent_runtime_arn" {
  description = "Chat Agent Runtime ARN"
  value       = awscc_bedrockagentcore_runtime.chat_agent.agent_runtime_arn
}

output "chat_memory_id" {
  description = "Chat AgentCore Memory ID"
  value       = aws_bedrockagentcore_memory.chat_memory.id
}

output "chat_memory_arn" {
  description = "Chat AgentCore Memory ARN"
  value       = aws_bedrockagentcore_memory.chat_memory.arn
}
