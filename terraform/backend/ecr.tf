# =============================================================================
# ECR Repositories - Separate for Research and Chat Agents
# =============================================================================

# ECR Repository for Research Agent Runtime
resource "aws_ecr_repository" "research_agent" {
  name                 = "bedrock/${local.project_name}-research-${local.suffix}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Automatically delete images when destroying

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    local.common_tags,
    {
      Name      = "${local.project_name}-research-ecr"
      AgentType = "research"
    }
  )
}

# Lifecycle policy for Research Agent
resource "aws_ecr_lifecycle_policy" "research_agent" {
  repository = aws_ecr_repository.research_agent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECR Repository for Chat Agent Runtime
resource "aws_ecr_repository" "chat_agent" {
  name                 = "bedrock/${local.project_name}-chat-${local.suffix}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Automatically delete images when destroying

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    local.common_tags,
    {
      Name      = "${local.project_name}-chat-ecr"
      AgentType = "chat"
    }
  )
}

# Lifecycle policy for Chat Agent
resource "aws_ecr_lifecycle_policy" "chat_agent" {
  repository = aws_ecr_repository.chat_agent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# =============================================================================
# Outputs
# =============================================================================

output "research_agent_ecr_url" {
  description = "ECR repository URL for Research Agent Docker images"
  value       = aws_ecr_repository.research_agent.repository_url
}

output "chat_agent_ecr_url" {
  description = "ECR repository URL for Chat Agent Docker images"
  value       = aws_ecr_repository.chat_agent.repository_url
}
