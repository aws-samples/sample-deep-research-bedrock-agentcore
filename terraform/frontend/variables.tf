variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "deep-research-agent"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "VPC ID for ECS and ALB (leave empty to create new VPC)"
  type        = string
  default     = ""
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB (leave empty to create new subnets)"
  type        = list(string)
  default     = []
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks (leave empty to create new subnets)"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    Project     = "DeepResearch"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}
