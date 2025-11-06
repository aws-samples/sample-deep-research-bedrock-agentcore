# ============================================================================
# Cognito User Pool for Authentication
# ============================================================================

resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-users-${var.environment}"

  # User attributes - use email as username
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # User pool schema
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # MFA configuration (optional)
  mfa_configuration = "OFF"

  # Allow users to sign up themselves
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-user-pool-${var.environment}"
    }
  )
}

# ============================================================================
# Cognito User Pool Client (for React App - no secret)
# ============================================================================

resource "aws_cognito_user_pool_client" "web_client" {
  name         = "${var.project_name}-web-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  # Web apps should not use client secret
  generate_secret = false

  # OAuth settings
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  callback_urls = [
    "http://localhost:3000",
    "http://localhost:3000/callback",
    "https://${aws_cloudfront_distribution.frontend.domain_name}",
    "https://${aws_cloudfront_distribution.frontend.domain_name}/callback"
  ]

  logout_urls = [
    "http://localhost:3000",
    "https://${aws_cloudfront_distribution.frontend.domain_name}"
  ]

  # Wait for CloudFront to be created first
  depends_on = [aws_cloudfront_distribution.frontend]

  supported_identity_providers = ["COGNITO"]

  # Token validity
  id_token_validity      = 60  # minutes
  access_token_validity  = 60  # minutes
  refresh_token_validity = 30  # days

  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "days"
  }

  # Security settings
  prevent_user_existence_errors = "ENABLED"

  read_attributes = [
    "email",
    "email_verified"
  ]

  write_attributes = [
    "email"
  ]

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]
}

# ============================================================================
# Cognito User Pool Client for ALB (with secret)
# ============================================================================

resource "aws_cognito_user_pool_client" "alb_client" {
  name         = "${var.project_name}-alb-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  # ALB requires client secret
  generate_secret = true

  # OAuth settings for ALB
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  callback_urls = [
    "https://${aws_cloudfront_distribution.frontend.domain_name}/oauth2/idpresponse"
  ]

  logout_urls = [
    "https://${aws_cloudfront_distribution.frontend.domain_name}"
  ]

  # Wait for CloudFront to be created first
  depends_on = [aws_cloudfront_distribution.frontend]

  supported_identity_providers = ["COGNITO"]

  # Token validity
  id_token_validity      = 60  # minutes
  access_token_validity  = 60  # minutes
  refresh_token_validity = 30  # days

  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "days"
  }

  # Security settings
  prevent_user_existence_errors = "ENABLED"
}

# ============================================================================
# Cognito User Pool Domain
# ============================================================================

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${var.environment}-${random_string.domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "random_string" "domain_suffix" {
  length  = 8
  special = false
  upper   = false
}

# ============================================================================
# Cognito Identity Pool (for AWS SDK in browser)
# ============================================================================

resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${var.project_name}_identity_pool_${var.environment}"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.web_client.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  tags = var.tags
}

# ============================================================================
# IAM Roles for Cognito Identity Pool
# ============================================================================

# Authenticated users role
resource "aws_iam_role" "authenticated" {
  name = "${var.project_name}-cognito-authenticated-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })

  tags = var.tags
}

# Authenticated users policy (minimal permissions)
resource "aws_iam_role_policy" "authenticated" {
  name = "authenticated-policy"
  role = aws_iam_role.authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${local.outputs_bucket}/users/$${cognito-identity.amazonaws.com:sub}/*"
        ]
      }
    ]
  })
}

# Attach identity pool roles
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    authenticated = aws_iam_role.authenticated.arn
  }
}
