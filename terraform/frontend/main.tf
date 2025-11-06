terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

# Data sources - reference backend resources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Get backend resources
data "terraform_remote_state" "backend" {
  backend = "local"

  config = {
    path = "../backend/terraform.tfstate"
  }
}

# Local values
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  # Get backend outputs
  agent_runtime_id         = data.terraform_remote_state.backend.outputs.agent_runtime_id
  agent_runtime_arn        = data.terraform_remote_state.backend.outputs.agent_runtime_arn
  memory_id                = data.terraform_remote_state.backend.outputs.agentcore_memory_id
  memory_arn               = data.terraform_remote_state.backend.outputs.agentcore_memory_arn
  chat_agent_runtime_id    = data.terraform_remote_state.backend.outputs.chat_agent_runtime_id
  chat_agent_runtime_arn   = data.terraform_remote_state.backend.outputs.chat_agent_runtime_arn
  chat_memory_id           = data.terraform_remote_state.backend.outputs.chat_memory_id
  chat_memory_arn          = data.terraform_remote_state.backend.outputs.chat_memory_arn
  status_table_name        = data.terraform_remote_state.backend.outputs.dynamodb_status_table
  user_preferences_table   = data.terraform_remote_state.backend.outputs.dynamodb_user_preferences_table
  outputs_bucket           = data.terraform_remote_state.backend.outputs.s3_outputs_bucket
}
