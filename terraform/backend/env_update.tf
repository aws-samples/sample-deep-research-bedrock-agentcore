# Automatically update .env file after Terraform apply
resource "null_resource" "update_env_file" {
  # Trigger on any output changes
  triggers = {
    dynamodb_table = aws_dynamodb_table.research_status.name
    s3_bucket      = aws_s3_bucket.research_outputs.bucket
    memory_id      = aws_bedrockagentcore_memory.research_memory.id
    region         = var.aws_region
  }

  # Run update script after Terraform apply
  provisioner "local-exec" {
    command     = "python3 ../../scripts/update_env.py || echo 'Warning: Failed to update .env file. Run manually: python scripts/update_env.py'"
    working_dir = path.module
    on_failure  = continue
  }

  depends_on = [
    aws_dynamodb_table.research_status,
    aws_s3_bucket.research_outputs,
    aws_bedrockagentcore_memory.research_memory
  ]
}
