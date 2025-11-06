# ============================================================================
# Tavily Lambda Function
# ============================================================================

resource "aws_lambda_function" "tavily" {
  function_name = "${var.project_name}-tavily-${local.suffix}"
  description   = "Tavily Search and Extract tools for AgentCore Gateway"

  filename         = "${path.module}/../build/tavily-lambda.zip"
  source_code_hash = fileexists("${path.module}/../build/tavily-lambda.zip") ? filebase64sha256("${path.module}/../build/tavily-lambda.zip") : null

  runtime = "python3.13"
  handler = "lambda_function.lambda_handler"
  role    = aws_iam_role.lambda_role.arn

  architectures = ["arm64"]

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      TAVILY_API_KEY_SECRET_ARN = aws_secretsmanager_secret.tavily_api_key.arn
      LOG_LEVEL                 = "INFO"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-tavily-${local.suffix}"
    }
  )
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "tavily" {
  name              = "/aws/lambda/${aws_lambda_function.tavily.function_name}"
  retention_in_days = 7

  tags = local.common_tags
}

# ============================================================================
# Lambda Permissions for Gateway
# ============================================================================

resource "aws_lambda_permission" "gateway_invoke_tavily" {
  statement_id  = "AllowGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.tavily.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_arn    = aws_bedrockagentcore_gateway.research_gateway.gateway_arn
}

resource "aws_lambda_permission" "gateway_invoke_wikipedia" {
  statement_id  = "AllowGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.wikipedia.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_arn    = aws_bedrockagentcore_gateway.research_gateway.gateway_arn
}

resource "aws_lambda_permission" "gateway_invoke_duckduckgo" {
  statement_id  = "AllowGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.duckduckgo.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_arn    = aws_bedrockagentcore_gateway.research_gateway.gateway_arn
}

resource "aws_lambda_permission" "gateway_invoke_google_search" {
  statement_id  = "AllowGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.google_search.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_arn    = aws_bedrockagentcore_gateway.research_gateway.gateway_arn
}

resource "aws_lambda_permission" "gateway_invoke_arxiv" {
  statement_id  = "AllowGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.arxiv.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_arn    = aws_bedrockagentcore_gateway.research_gateway.gateway_arn
}

resource "aws_lambda_permission" "gateway_invoke_finance" {
  statement_id  = "AllowGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finance.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_arn    = aws_bedrockagentcore_gateway.research_gateway.gateway_arn
}

# ============================================================================
# Wikipedia Lambda Function
# ============================================================================

resource "aws_lambda_function" "wikipedia" {
  function_name = "${var.project_name}-wikipedia-${local.suffix}"
  description   = "Wikipedia search and article retrieval for AgentCore Gateway"

  filename         = "${path.module}/../build/wikipedia-lambda.zip"
  source_code_hash = fileexists("${path.module}/../build/wikipedia-lambda.zip") ? filebase64sha256("${path.module}/../build/wikipedia-lambda.zip") : null

  runtime = "python3.13"
  handler = "lambda_function.lambda_handler"
  role    = aws_iam_role.lambda_role.arn

  architectures = ["arm64"]

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-wikipedia-${local.suffix}"
    }
  )
}

resource "aws_cloudwatch_log_group" "wikipedia" {
  name              = "/aws/lambda/${aws_lambda_function.wikipedia.function_name}"
  retention_in_days = 7

  tags = local.common_tags
}

# ============================================================================
# DuckDuckGo Lambda Function
# ============================================================================

resource "aws_lambda_function" "duckduckgo" {
  function_name = "${var.project_name}-duckduckgo-${local.suffix}"
  description   = "DuckDuckGo web and news search for AgentCore Gateway"

  filename         = "${path.module}/../build/duckduckgo-lambda.zip"
  source_code_hash = fileexists("${path.module}/../build/duckduckgo-lambda.zip") ? filebase64sha256("${path.module}/../build/duckduckgo-lambda.zip") : null

  runtime = "python3.13"
  handler = "lambda_function.lambda_handler"
  role    = aws_iam_role.lambda_role.arn

  architectures = ["arm64"]

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-duckduckgo-${local.suffix}"
    }
  )
}

resource "aws_cloudwatch_log_group" "duckduckgo" {
  name              = "/aws/lambda/${aws_lambda_function.duckduckgo.function_name}"
  retention_in_days = 7

  tags = local.common_tags
}

# ============================================================================
# Google Search Lambda Function
# ============================================================================

resource "aws_lambda_function" "google_search" {
  function_name = "${var.project_name}-google-search-${local.suffix}"
  description   = "Google Custom Search for web and images via AgentCore Gateway"

  filename         = "${path.module}/../build/google-search-lambda.zip"
  source_code_hash = fileexists("${path.module}/../build/google-search-lambda.zip") ? filebase64sha256("${path.module}/../build/google-search-lambda.zip") : null

  runtime = "python3.13"
  handler = "lambda_function.lambda_handler"
  role    = aws_iam_role.lambda_role.arn

  architectures = ["arm64"]

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      GOOGLE_CREDENTIALS_SECRET_ARN = aws_secretsmanager_secret.google_credentials.arn
      LOG_LEVEL                     = "INFO"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-google-search-${local.suffix}"
    }
  )
}

resource "aws_cloudwatch_log_group" "google_search" {
  name              = "/aws/lambda/${aws_lambda_function.google_search.function_name}"
  retention_in_days = 7

  tags = local.common_tags
}

# ============================================================================
# ArXiv Lambda Function
# ============================================================================

resource "aws_lambda_function" "arxiv" {
  function_name = "${var.project_name}-arxiv-${local.suffix}"
  description   = "ArXiv paper search and retrieval for AgentCore Gateway"

  filename         = "${path.module}/../build/arxiv-lambda.zip"
  source_code_hash = fileexists("${path.module}/../build/arxiv-lambda.zip") ? filebase64sha256("${path.module}/../build/arxiv-lambda.zip") : null

  runtime = "python3.13"
  handler = "lambda_function.lambda_handler"
  role    = aws_iam_role.lambda_role.arn

  architectures = ["arm64"]

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-arxiv-${local.suffix}"
    }
  )
}

resource "aws_cloudwatch_log_group" "arxiv" {
  name              = "/aws/lambda/${aws_lambda_function.arxiv.function_name}"
  retention_in_days = 7

  tags = local.common_tags
}

# ============================================================================
# Finance Lambda Function
# ============================================================================

# ECR repository for Finance Lambda container (reference existing)
data "aws_ecr_repository" "finance_lambda" {
  name = "research-tools-finance-lambda"
}

data "aws_ecr_image" "finance_lambda" {
  repository_name = data.aws_ecr_repository.finance_lambda.name
  image_tag       = "latest"
}

resource "aws_lambda_function" "finance" {
  function_name = "${var.project_name}-finance-${local.suffix}"
  description   = "Yahoo Finance stock data and analysis for AgentCore Gateway"

  # Use container image instead of ZIP
  package_type = "Image"
  image_uri    = "${data.aws_ecr_repository.finance_lambda.repository_url}:latest"

  role = aws_iam_role.lambda_role.arn

  architectures = ["arm64"]

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  # For AWS Lambda Python base images, use Dockerfile CMD instead of image_config
  # The base image's entrypoint will read the CMD as the handler
  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-finance-${local.suffix}"
    }
  )

  depends_on = [data.aws_ecr_image.finance_lambda]
}

resource "aws_cloudwatch_log_group" "finance" {
  name              = "/aws/lambda/${aws_lambda_function.finance.function_name}"
  retention_in_days = 7

  tags = local.common_tags
}
