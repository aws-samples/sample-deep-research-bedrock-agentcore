# S3 Bucket for Research Outputs (reports, documents)
resource "aws_s3_bucket" "research_outputs" {
  bucket        = "${local.project_name}-outputs-${local.suffix}"
  force_destroy = true  # Allow Terraform to delete bucket even with objects

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-outputs"
  })
}

resource "aws_s3_bucket_versioning" "research_outputs" {
  bucket = aws_s3_bucket.research_outputs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "research_outputs" {
  bucket = aws_s3_bucket.research_outputs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "research_outputs" {
  bucket = aws_s3_bucket.research_outputs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "research_outputs" {
  bucket = aws_s3_bucket.research_outputs.id

  rule {
    id     = "delete-old-reports"
    status = "Enabled"

    filter {}  # Apply to all objects

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

output "s3_outputs_bucket" {
  description = "S3 bucket for research outputs"
  value       = aws_s3_bucket.research_outputs.bucket
}
