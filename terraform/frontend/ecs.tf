# ============================================================================
# ECS Cluster
# ============================================================================

resource "aws_ecs_cluster" "frontend" {
  name = "${var.project_name}-frontend-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# ============================================================================
# ECR Repository for Frontend
# ============================================================================

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Allow deletion even with images

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# ============================================================================
# ECS Task Definition
# ============================================================================

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"  # 0.5 vCPU
  memory                   = "1024" # 1 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = "${aws_ecr_repository.frontend.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "NODE_ENV"
          value = "production"
        },
        {
          name  = "PORT"
          value = "8000"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "PROJECT_NAME"
          value = var.project_name
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "CORS_ORIGIN"
          value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
        },
        {
          name  = "ENABLE_AUTH"
          value = "true"
        },
        {
          name  = "COGNITO_USER_POOL_ID"
          value = aws_cognito_user_pool.main.id
        },
        {
          name  = "COGNITO_CLIENT_ID"
          value = aws_cognito_user_pool_client.web_client.id
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = var.tags
}

# ============================================================================
# ECS Service
# ============================================================================

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend-${var.environment}"
  cluster         = aws_ecs_cluster.frontend.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : local.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 8000
  }

  # Give ECS time to start and pass health checks before marking as unhealthy
  health_check_grace_period_seconds = 120  # 2 minutes

  depends_on = [aws_lb_listener.http]

  tags = var.tags
}

# ============================================================================
# CloudWatch Log Group
# ============================================================================

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}-frontend-${var.environment}"
  retention_in_days = 7

  tags = var.tags
}

# ============================================================================
# IAM Roles
# ============================================================================

# ECS Execution Role (for pulling images, writing logs)
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application to access AWS services)
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "ecs_task" {
  name = "ecs-task-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AgentCoreRuntimeInvoke"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:InvokeAgentRuntimeForUser"
        ]
        Resource = [
          local.agent_runtime_arn,
          "${local.agent_runtime_arn}/*",
          local.chat_agent_runtime_arn,
          "${local.chat_agent_runtime_arn}/*"
        ]
      },
      {
        Sid    = "AgentCoreMemoryFullAccess"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:*Memory*",
          "bedrock-agentcore:*Event*",
          "bedrock-agentcore:*Session*"
        ]
        Resource = [
          local.memory_arn,
          "${local.memory_arn}/*",
          local.chat_memory_arn,
          "${local.chat_memory_arn}/*"
        ]
      },
      {
        Sid    = "SSMParameterAccess"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${local.region}:${local.account_id}:parameter/${var.project_name}/${var.environment}/*"
        ]
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          "arn:aws:dynamodb:${local.region}:${local.account_id}:table/${local.status_table_name}",
          "arn:aws:dynamodb:${local.region}:${local.account_id}:table/${local.status_table_name}/index/*",
          "arn:aws:dynamodb:${local.region}:${local.account_id}:table/${local.user_preferences_table}"
        ]
      },
      {
        Sid    = "S3OutputsAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${local.outputs_bucket}",
          "arn:aws:s3:::${local.outputs_bucket}/*"
        ]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${local.region}:${local.account_id}:log-group:/ecs/${var.project_name}-frontend-${var.environment}:*"
      }
    ]
  })
}

# ============================================================================
# Security Group for ECS Tasks
# ============================================================================

resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-${var.environment}"
  description = "Security group for ECS tasks"
  vpc_id      = length(var.vpc_id) > 0 ? var.vpc_id : local.vpc_id

  ingress {
    description     = "Allow traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-ecs-tasks-${var.environment}"
    }
  )
}
