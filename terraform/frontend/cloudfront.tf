# ============================================================================
# CloudFront Distribution
# ============================================================================

resource "aws_cloudfront_distribution" "frontend" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "${var.project_name} Frontend Distribution"
  price_class     = "PriceClass_100" # Use only North America and Europe

  # ALB Origin
  origin {
    domain_name = aws_lb.frontend.dns_name
    origin_id   = "ALB-${var.project_name}"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only" # ALB handles HTTPS internally
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60  # Maximum allowed by CloudFront
      origin_keepalive_timeout = 60  # Maximum allowed by CloudFront
    }

    custom_header {
      name  = "X-Custom-Header"
      value = random_string.cloudfront_secret.result
    }
  }

  # Default cache behavior
  default_cache_behavior {
    target_origin_id       = "ALB-${var.project_name}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # Cache policy for static files
    cache_policy_id = aws_cloudfront_cache_policy.static_files.id

    # Origin request policy to forward headers
    origin_request_policy_id = aws_cloudfront_origin_request_policy.all_viewer.id
  }

  # API behavior (no caching)
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "ALB-${var.project_name}"
    viewer_protocol_policy = "https-only"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # No caching for API
    cache_policy_id = aws_cloudfront_cache_policy.no_cache.id

    # Forward all headers/cookies for API
    origin_request_policy_id = aws_cloudfront_origin_request_policy.all_viewer.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    # For custom domain:
    # acm_certificate_arn      = aws_acm_certificate.cloudfront.arn
    # ssl_support_method       = "sni-only"
    # minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = var.tags
}

# ============================================================================
# CloudFront Cache Policies
# ============================================================================

# Cache policy for static files (React build)
resource "aws_cloudfront_cache_policy" "static_files" {
  name        = "${var.project_name}-static-files-${var.environment}"
  comment     = "Cache policy for static files"
  default_ttl = 3600
  max_ttl     = 86400
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }

    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true
  }
}

# No-cache policy for API
resource "aws_cloudfront_cache_policy" "no_cache" {
  name        = "${var.project_name}-no-cache-${var.environment}"
  comment     = "No caching for API requests"
  default_ttl = 0
  max_ttl     = 0
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"  # Must be "none" when caching is disabled
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"  # Must be "none" when caching is disabled
    }

    enable_accept_encoding_gzip   = false
    enable_accept_encoding_brotli = false
  }
}

# ============================================================================
# CloudFront Origin Request Policies
# ============================================================================

resource "aws_cloudfront_origin_request_policy" "all_viewer" {
  name    = "${var.project_name}-all-viewer-${var.environment}"
  comment = "Forward all viewer headers, cookies, and query strings"

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "allViewer"
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# ============================================================================
# Random secret for CloudFront custom header
# ============================================================================

resource "random_string" "cloudfront_secret" {
  length  = 32
  special = false
}

# Note: ALB security group rules already defined in alb.tf
# No need to duplicate here
