# =============================================================================
# CodeBuild Projects - Separate for Research and Chat Agents
# =============================================================================

# CodeBuild Project for Research Agent Docker Image
resource "aws_codebuild_project" "research_agent_build" {
  name          = "${local.project_name}-research-build-${local.suffix}"
  description   = "Build Docker image for Research Agent (LangGraph)"
  service_role  = aws_iam_role.codebuild_role.arn
  build_timeout = 30

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-aarch64-standard:3.0"
    type                        = "ARM_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "ECR_REPOSITORY_URI"
      value = aws_ecr_repository.research_agent.repository_url
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = "research-agent"
    }
  }

  source {
    type      = "S3"
    location  = "${aws_s3_bucket.codebuild_artifacts.bucket}/research-agent-source.zip"
    buildspec = "research-agent/buildspec.yml"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "/aws/codebuild/${local.project_name}"
      stream_name = "research-agent-build"
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-research-build"
    AgentType = "research"
  })
}

# CodeBuild Project for Chat Agent Docker Image
resource "aws_codebuild_project" "chat_agent_build" {
  name          = "${local.project_name}-chat-build-${local.suffix}"
  description   = "Build Docker image for Chat Agent (Strands)"
  service_role  = aws_iam_role.codebuild_role.arn
  build_timeout = 15  # Shorter timeout for lightweight chat agent

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-aarch64-standard:3.0"
    type                        = "ARM_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "ECR_REPOSITORY_URI"
      value = aws_ecr_repository.chat_agent.repository_url
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = "chat-agent"
    }
  }

  source {
    type      = "S3"
    location  = "${aws_s3_bucket.codebuild_artifacts.bucket}/chat-agent-source.zip"
    buildspec = "chat-agent/buildspec.yml"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "/aws/codebuild/${local.project_name}"
      stream_name = "chat-agent-build"
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-chat-build"
    AgentType = "chat"
  })
}

# =============================================================================
# Shared IAM Resources
# =============================================================================

# IAM Role for CodeBuild
resource "aws_iam_role" "codebuild_role" {
  name = "${local.project_name}-codebuild-role-${local.suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for CodeBuild
resource "aws_iam_role_policy" "codebuild_policy" {
  role = aws_iam_role.codebuild_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/codebuild/${local.project_name}*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.codebuild_artifacts.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.codebuild_artifacts.arn
      }
    ]
  })
}

# S3 Bucket for CodeBuild Source (temporary)
resource "aws_s3_bucket" "codebuild_artifacts" {
  bucket        = "${local.project_name}-codebuild-${local.suffix}"
  force_destroy = true  # Allow Terraform to delete bucket even with objects

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-codebuild"
  })
}

resource "aws_s3_bucket_versioning" "codebuild_artifacts" {
  bucket = aws_s3_bucket.codebuild_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "codebuild_artifacts" {
  bucket = aws_s3_bucket.codebuild_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# Outputs
# =============================================================================

output "research_agent_codebuild_project" {
  description = "CodeBuild project name for Research Agent image builds"
  value       = aws_codebuild_project.research_agent_build.name
}

output "chat_agent_codebuild_project" {
  description = "CodeBuild project name for Chat Agent image builds"
  value       = aws_codebuild_project.chat_agent_build.name
}
