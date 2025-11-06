# DynamoDB Table for Research Status
resource "aws_dynamodb_table" "research_status" {
  name           = "${local.project_name}-status-${local.suffix}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "updated_at"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  # GSI for querying by status
  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "updated_at"
    projection_type = "ALL"
  }

  # GSI for querying by user_id (for user history)
  global_secondary_index {
    name            = "user-id-index"
    hash_key        = "user_id"
    range_key       = "updated_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-status"
  })
}

output "dynamodb_status_table" {
  description = "DynamoDB status table name"
  value       = aws_dynamodb_table.research_status.name
}

# DynamoDB Table for User Preferences
resource "aws_dynamodb_table" "user_preferences" {
  name           = "${local.project_name}-user-preferences-${local.suffix}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-user-preferences"
  })
}

output "dynamodb_user_preferences_table" {
  description = "DynamoDB user preferences table name"
  value       = aws_dynamodb_table.user_preferences.name
}
