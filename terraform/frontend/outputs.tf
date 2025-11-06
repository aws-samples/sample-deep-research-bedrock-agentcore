output "cloudfront_domain_name" {
  description = "CloudFront Distribution Domain Name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_url" {
  description = "CloudFront Distribution URL"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS Name"
  value       = aws_lb.frontend.dns_name
}

output "ecr_repository_url" {
  description = "ECR Repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.frontend.name
}

output "ecs_service_name" {
  description = "ECS Service Name"
  value       = aws_ecs_service.frontend.name
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.web_client.id
}

output "cognito_identity_pool_id" {
  description = "Cognito Identity Pool ID"
  value       = aws_cognito_identity_pool.main.id
}

output "cognito_domain" {
  description = "Cognito User Pool Domain"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "cognito_hosted_ui_url" {
  description = "Cognito Hosted UI Login URL (for ALB)"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com/login?client_id=${aws_cognito_user_pool_client.alb_client.id}&response_type=code&redirect_uri=https://${aws_cloudfront_distribution.frontend.domain_name}/oauth2/idpresponse"
}

output "cognito_alb_client_id" {
  description = "Cognito User Pool Client ID for ALB"
  value       = aws_cognito_user_pool_client.alb_client.id
}

output "frontend_config" {
  description = "Frontend configuration"
  value = {
    REACT_APP_API_URL              = "https://${aws_cloudfront_distribution.frontend.domain_name}"
    REACT_APP_AWS_REGION           = var.aws_region
    REACT_APP_USER_POOL_ID         = aws_cognito_user_pool.main.id
    REACT_APP_USER_POOL_CLIENT_ID  = aws_cognito_user_pool_client.web_client.id
    REACT_APP_IDENTITY_POOL_ID     = aws_cognito_identity_pool.main.id
    REACT_APP_ENABLE_AUTH          = "true"
  }
}
