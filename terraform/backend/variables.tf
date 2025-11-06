variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "log_level" {
  description = "Log level for the application"
  type        = string
  default     = "INFO"
}

variable "enable_xray" {
  description = "Enable AWS X-Ray tracing"
  type        = bool
  default     = false
}

# Tool API Keys (temporary - set sensitive values in terraform.tfvars)
variable "tavily_api_key" {
  description = "Tavily API key for web search"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_api_key" {
  description = "Google Custom Search API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_search_engine_id" {
  description = "Google Custom Search Engine ID"
  type        = string
  default     = ""
  sensitive   = true
}

# LangSmith Configuration
variable "langchain_tracing_enabled" {
  description = "Enable LangSmith tracing"
  type        = string
  default     = "false"
}

variable "langchain_project" {
  description = "LangSmith project name"
  type        = string
  default     = "deep-research-agent"
}

variable "langchain_api_key" {
  description = "LangSmith API key"
  type        = string
  default     = ""
  sensitive   = true
}
