# ============================================================================
# Gateway Outputs - Active
# ============================================================================

output "gateway_id" {
  description = "Gateway ID"
  value       = aws_bedrockagentcore_gateway.research_gateway.gateway_id
}

output "gateway_url" {
  description = "Gateway URL for MCP connections"
  value       = aws_bedrockagentcore_gateway.research_gateway.gateway_url
}

output "gateway_arn" {
  description = "Gateway ARN"
  value       = aws_bedrockagentcore_gateway.research_gateway.gateway_arn
}

output "gateway_config" {
  description = "Gateway configuration for agent runtime"
  value = {
    gateway_url = aws_bedrockagentcore_gateway.research_gateway.gateway_url
    gateway_id  = aws_bedrockagentcore_gateway.research_gateway.gateway_id
    region      = data.aws_region.current.id
    auth_mode   = "IAM"
    tools = [
      # Tavily
      "tavily_search",
      "tavily_extract",
      # Wikipedia
      "wikipedia_search",
      "wikipedia_get_article",
      # DuckDuckGo
      "ddg_search",
      "ddg_news",
      # Google
      "google_web_search",
      "google_image_search",
      # ArXiv
      "arxiv_search",
      "arxiv_get_paper",
      # Finance
      "stock_quote",
      "stock_history",
      "financial_news",
      "stock_analysis"
    ]
  }
}

# ============================================================================
# Lambda Outputs - Active
# ============================================================================

output "tavily_lambda_arn" {
  description = "Tavily Lambda function ARN"
  value       = aws_lambda_function.tavily.arn
}

output "tavily_lambda_name" {
  description = "Tavily Lambda function name"
  value       = aws_lambda_function.tavily.function_name
}

output "wikipedia_lambda_arn" {
  description = "Wikipedia Lambda function ARN"
  value       = aws_lambda_function.wikipedia.arn
}

output "wikipedia_lambda_name" {
  description = "Wikipedia Lambda function name"
  value       = aws_lambda_function.wikipedia.function_name
}

output "duckduckgo_lambda_arn" {
  description = "DuckDuckGo Lambda function ARN"
  value       = aws_lambda_function.duckduckgo.arn
}

output "duckduckgo_lambda_name" {
  description = "DuckDuckGo Lambda function name"
  value       = aws_lambda_function.duckduckgo.function_name
}

output "google_search_lambda_arn" {
  description = "Google Search Lambda function ARN"
  value       = aws_lambda_function.google_search.arn
}

output "google_search_lambda_name" {
  description = "Google Search Lambda function name"
  value       = aws_lambda_function.google_search.function_name
}

output "arxiv_lambda_arn" {
  description = "ArXiv Lambda function ARN"
  value       = aws_lambda_function.arxiv.arn
}

output "arxiv_lambda_name" {
  description = "ArXiv Lambda function name"
  value       = aws_lambda_function.arxiv.function_name
}

output "finance_lambda_arn" {
  description = "Finance Lambda function ARN"
  value       = aws_lambda_function.finance.arn
}

output "finance_lambda_name" {
  description = "Finance Lambda function name"
  value       = aws_lambda_function.finance.function_name
}

output "all_lambda_arns" {
  description = "All Lambda function ARNs"
  value = {
    tavily       = aws_lambda_function.tavily.arn
    wikipedia    = aws_lambda_function.wikipedia.arn
    duckduckgo   = aws_lambda_function.duckduckgo.arn
    google_search = aws_lambda_function.google_search.arn
    arxiv        = aws_lambda_function.arxiv.arn
    finance      = aws_lambda_function.finance.arn
  }
}

output "region" {
  description = "AWS Region"
  value       = data.aws_region.current.id
}

# ============================================================================
# Parameter Store Outputs
# ============================================================================

output "parameter_store_config" {
  description = "Parameter Store configuration paths for agent runtime"
  value = {
    agentcore_memory_id   = aws_ssm_parameter.agentcore_memory_id.name
    dynamodb_status_table = aws_ssm_parameter.dynamodb_status_table.name
    s3_outputs_bucket     = aws_ssm_parameter.s3_outputs_bucket.name
    aws_region            = aws_ssm_parameter.aws_region.name
    gateway_url           = aws_ssm_parameter.gateway_url.name
    langchain_project     = var.langchain_project != "" ? aws_ssm_parameter.langchain_project[0].name : null
    langchain_tracing_v2  = var.langchain_tracing_v2 != "" ? aws_ssm_parameter.langchain_tracing[0].name : null
  }
}

output "secrets_manager_config" {
  description = "Secrets Manager ARNs for agent runtime"
  sensitive   = true
  value = {
    tavily_api_key    = aws_secretsmanager_secret.tavily_api_key.arn
    google_credentials = aws_secretsmanager_secret.google_credentials.arn
    langchain_api_key = var.langchain_api_key != "" ? aws_secretsmanager_secret.langchain_api_key[0].arn : null
  }
}

output "agent_runtime_config" {
  description = "Complete configuration for agent runtime (.env loading)"
  sensitive   = true
  value = {
    # Parameter Store paths (agent should load these at runtime)
    parameters = {
      agentcore_memory_id   = aws_ssm_parameter.agentcore_memory_id.name
      dynamodb_status_table = aws_ssm_parameter.dynamodb_status_table.name
      s3_outputs_bucket     = aws_ssm_parameter.s3_outputs_bucket.name
      gateway_url           = aws_ssm_parameter.gateway_url.name
      aws_region            = aws_ssm_parameter.aws_region.name
    }
    # Secrets Manager ARNs (agent should load these at runtime)
    secrets = {
      tavily_api_key     = aws_secretsmanager_secret.tavily_api_key.arn
      google_api_key     = aws_secretsmanager_secret.google_credentials.arn
      langchain_api_key  = var.langchain_api_key != "" ? aws_secretsmanager_secret.langchain_api_key[0].arn : null
    }
    # Static configuration (can remain in .env)
    static = {
      region = data.aws_region.current.id
    }
  }
}
