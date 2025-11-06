# ============================================================================
# Lambda Execution Role
# ============================================================================

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${local.suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for accessing ECR (for container-based Lambda)
resource "aws_iam_policy" "lambda_ecr" {
  name        = "${var.project_name}-lambda-ecr-${local.suffix}"
  description = "Allow Lambda to pull images from ECR"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_ecr" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_ecr.arn
}

# Policy for accessing Secrets Manager (API Keys)
resource "aws_iam_policy" "lambda_secrets" {
  name        = "${var.project_name}-lambda-secrets-${local.suffix}"
  description = "Allow Lambda to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.tavily_api_key.arn,
          aws_secretsmanager_secret.google_credentials.arn
        ]
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_secrets.arn
}

# ============================================================================
# Gateway Execution Role
# ============================================================================

resource "aws_iam_role" "gateway_role" {
  name = "${var.project_name}-gateway-role-${local.suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "bedrock-agentcore.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

# Gateway needs permission to invoke Lambda
resource "aws_iam_policy" "gateway_lambda_invoke" {
  name        = "${var.project_name}-gateway-lambda-${local.suffix}"
  description = "Allow Gateway to invoke Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.tavily.arn,
          aws_lambda_function.wikipedia.arn,
          aws_lambda_function.duckduckgo.arn,
          aws_lambda_function.google_search.arn,
          aws_lambda_function.arxiv.arn,
          aws_lambda_function.finance.arn
        ]
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "gateway_lambda_invoke" {
  role       = aws_iam_role.gateway_role.name
  policy_arn = aws_iam_policy.gateway_lambda_invoke.arn
}

# ============================================================================
# Secrets Manager for API Keys
# ============================================================================

resource "aws_secretsmanager_secret" "tavily_api_key" {
  name        = "${var.project_name}-tavily-api-key-${local.suffix}"
  description = "Tavily API Key for research tools"

  # Force overwrite if secret is scheduled for deletion
  force_overwrite_replica_secret = true

  # Set to 0 to immediately delete when terraform destroy is called
  recovery_window_in_days = 0

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "tavily_api_key" {
  secret_id     = aws_secretsmanager_secret.tavily_api_key.id
  secret_string = var.tavily_api_key
}

# Google Custom Search Credentials
resource "aws_secretsmanager_secret" "google_credentials" {
  name        = "${var.project_name}-google-credentials-${local.suffix}"
  description = "Google Custom Search API credentials"

  # Force overwrite if secret is scheduled for deletion
  force_overwrite_replica_secret = true

  # Set to 0 to immediately delete when terraform destroy is called
  recovery_window_in_days = 0

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "google_credentials" {
  secret_id = aws_secretsmanager_secret.google_credentials.id
  secret_string = jsonencode({
    api_key          = var.google_api_key
    search_engine_id = var.google_search_engine_id
  })
}
