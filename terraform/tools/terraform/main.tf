terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"  # AgentCore Gateway with AWS_IAM support
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Generate unique suffix for resources
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  suffix = random_string.suffix.result

  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Suffix      = local.suffix
    }
  )
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
