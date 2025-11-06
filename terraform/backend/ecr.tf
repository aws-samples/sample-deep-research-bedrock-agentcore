# =============================================================================
# ECR Repositories - Separate for Research and Chat Agents
# =============================================================================

# ECR Repository for Research Agent Runtime
resource "awscc_ecr_repository" "research_agent" {
  repository_name = "bedrock/${local.project_name}-research-${local.suffix}"

  image_scanning_configuration = {
    scan_on_push = true
  }

  lifecycle_policy = {
    lifecycle_policy_text = jsonencode({
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

  tags = [
    {
      key   = "Project"
      value = local.common_tags.Project
    },
    {
      key   = "Environment"
      value = local.common_tags.Environment
    },
    {
      key   = "ManagedBy"
      value = local.common_tags.ManagedBy
    },
    {
      key   = "AgentType"
      value = "research"
    }
  ]
}

# ECR Repository for Chat Agent Runtime
resource "awscc_ecr_repository" "chat_agent" {
  repository_name = "bedrock/${local.project_name}-chat-${local.suffix}"

  image_scanning_configuration = {
    scan_on_push = true
  }

  lifecycle_policy = {
    lifecycle_policy_text = jsonencode({
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

  tags = [
    {
      key   = "Project"
      value = local.common_tags.Project
    },
    {
      key   = "Environment"
      value = local.common_tags.Environment
    },
    {
      key   = "ManagedBy"
      value = local.common_tags.ManagedBy
    },
    {
      key   = "AgentType"
      value = "chat"
    }
  ]
}

# =============================================================================
# Outputs
# =============================================================================

output "research_agent_ecr_url" {
  description = "ECR repository URL for Research Agent Docker images"
  value       = awscc_ecr_repository.research_agent.repository_uri
}

output "chat_agent_ecr_url" {
  description = "ECR repository URL for Chat Agent Docker images"
  value       = awscc_ecr_repository.chat_agent.repository_uri
}
