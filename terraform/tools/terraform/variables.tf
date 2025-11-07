variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Project name for resource naming (must match backend)"
  type        = string
  default     = "deep-research-agent"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "tavily_api_key" {
  description = "Tavily API key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "google_api_key" {
  description = "Google Custom Search API key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_search_engine_id" {
  description = "Google Custom Search Engine ID (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 180
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "Research Gateway"
    ManagedBy = "Terraform"
  }
}

# ============================================================================
# Configuration values to be stored in Parameter Store
# ============================================================================

variable "agentcore_memory_id" {
  description = "AgentCore Memory ID from parent deployment"
  type        = string
}

variable "dynamodb_status_table" {
  description = "DynamoDB table name for status tracking from parent deployment"
  type        = string
}

variable "s3_outputs_bucket" {
  description = "S3 bucket name for outputs from parent deployment"
  type        = string
}

# ============================================================================
# Optional: LangSmith Configuration
# ============================================================================

variable "langchain_api_key" {
  description = "LangSmith API key for tracing (optional, stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "langchain_project" {
  description = "LangSmith project name (optional)"
  type        = string
  default     = ""
}

variable "langchain_tracing_v2" {
  description = "Enable LangSmith tracing V2 (optional)"
  type        = string
  default     = ""
}
