# ============================================================================
# Application Load Balancer
# ============================================================================

resource "aws_lb" "frontend" {
  name               = "${var.project_name}-frontend-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = length(var.public_subnet_ids) > 0 ? var.public_subnet_ids : local.public_subnet_ids

  enable_deletion_protection = false
  enable_http2               = true
  idle_timeout               = 3600  # 1 hour (max is 4000 seconds)

  tags = var.tags
}

# ============================================================================
# Target Group
# ============================================================================

resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = length(var.vpc_id) > 0 ? var.vpc_id : local.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 5  # Increased from 3 to 5 (more tolerant)
    timeout             = 10  # Increased from 5 to 10 seconds
    interval            = 30
    path                = "/api/health"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = var.tags
}

# ============================================================================
# Listeners
# ============================================================================

# HTTP Listener (forward directly - HTTPS handled by CloudFront)
# Authentication handled by React app (Amplify)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# HTTPS Listener (optional - only if certificate exists)
# Commented out for initial deployment
# Uncomment after setting up a custom domain with ACM certificate

# resource "aws_lb_listener" "https" {
#   load_balancer_arn = aws_lb.frontend.arn
#   port              = "443"
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
#   certificate_arn   = aws_acm_certificate.frontend.arn
#
#   default_action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.frontend.arn
#   }
# }

# ============================================================================
# Security Group for ALB
# ============================================================================

resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-${var.environment}"
  description = "Security group for Application Load Balancer"
  vpc_id      = length(var.vpc_id) > 0 ? var.vpc_id : local.vpc_id

  ingress {
    description = "Allow HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-alb-${var.environment}"
    }
  )
}

# ============================================================================
# ACM Certificate (Optional - for custom domain)
# ============================================================================

# Note: Commented out for initial deployment
# Uncomment and configure when you have a custom domain

# resource "aws_acm_certificate" "frontend" {
#   domain_name       = "your-domain.com"
#   validation_method = "DNS"
#
#   lifecycle {
#     create_before_destroy = true
#   }
#
#   tags = var.tags
# }
#
# resource "aws_route53_record" "cert_validation" {
#   for_each = {
#     for dvo in aws_acm_certificate.frontend.domain_validation_options : dvo.domain_name => {
#       name   = dvo.resource_record_name
#       record = dvo.resource_record_value
#       type   = dvo.resource_record_type
#     }
#   }
#
#   allow_overwrite = true
#   name            = each.value.name
#   records         = [each.value.record]
#   ttl             = 60
#   type            = each.value.type
#   zone_id         = var.route53_zone_id
# }
