output "summary" {
  description = "Deployment summary"
  value = {
    project_name = local.project_name
    environment  = var.environment
    region       = var.aws_region
    suffix       = local.suffix

    ecr_repositories = {
      research_agent = awscc_ecr_repository.research_agent.repository_uri
      chat_agent     = awscc_ecr_repository.chat_agent.repository_uri
    }

    agentcore_runtimes = {
      research_agent = {
        id      = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_id
        arn     = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_arn
        version = awscc_bedrockagentcore_runtime.research_agent.agent_runtime_version
        status  = awscc_bedrockagentcore_runtime.research_agent.status
      }
      chat_agent = {
        id      = awscc_bedrockagentcore_runtime.chat_agent.agent_runtime_id
        arn     = awscc_bedrockagentcore_runtime.chat_agent.agent_runtime_arn
        version = awscc_bedrockagentcore_runtime.chat_agent.agent_runtime_version
        status  = awscc_bedrockagentcore_runtime.chat_agent.status
      }
    }

    dynamodb_tables = {
      status = aws_dynamodb_table.research_status.name
      user_preferences = aws_dynamodb_table.user_preferences.name
    }

    s3_bucket = aws_s3_bucket.research_outputs.bucket

    iam_role_arn = awscc_iam_role.agent_runtime_role.arn
  }
}
