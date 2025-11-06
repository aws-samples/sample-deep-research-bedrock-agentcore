terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.18.0"  # Required for BedrockAgentCore Memory
    }
    awscc = {
      source  = "hashicorp/awscc"
      version = "~> 1.0"
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

provider "awscc" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  project_name = "deep-research-agent"
  suffix       = random_id.suffix.hex

  common_tags = {
    Project     = "DeepResearchAgent"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
