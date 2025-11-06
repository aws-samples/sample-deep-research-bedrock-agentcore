# Deployment Guide

This guide covers deploying the Dimensional Research Agent to AWS using Terraform.

## Prerequisites

- **AWS CLI** configured with credentials
- **Terraform** v1.0+
- **Docker** (for frontend deployment)
- **Node.js** & npm (for frontend build)

## Quick Deploy

```bash
./deploy.sh
```

Choose from the interactive menu:
1. **Backend** - AgentCore Runtime + Infrastructure
2. **Frontend** - Cognito + ECS + CloudFront
3. **Tools** - Gateway + Lambda functions
4. **Full Stack** - Backend + Frontend
5. **Everything** - All components

## Step-by-Step Deployment

### 1. Configure Environment Variables

Copy and edit `.env.example` to `.env`:

```bash
cp .env.example .env
```

Required variables (auto-populated after backend deployment):
- `AWS_REGION` - AWS deployment region
- `MEMORY_ID` - AgentCore Memory ID

Optional API keys:
- `TAVILY_API_KEY` - Tavily search (recommended)
- `GOOGLE_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` - Google search
- `LANGCHAIN_API_KEY` - LangSmith tracing (optional)

### 2. Deploy Backend

```bash
./terraform/deploy-backend.sh
```

This deploys:
- **AgentCore Runtime** - Research and Chat agents
- **DynamoDB** - Status tracking and user preferences
- **S3** - Research outputs storage
- **ECR** - Container registries
- **CodeBuild** - Automated Docker builds
- **AgentCore Memory** - Persistent memory with semantic search

The script automatically:
- Builds and pushes Docker images via CodeBuild
- Updates `.env` with resource IDs
- Creates all required AWS resources

**Outputs:**
- Research Agent Runtime ID
- Chat Agent Runtime ID
- DynamoDB table names
- S3 bucket name
- Memory ID

### 3. Deploy Frontend

```bash
./terraform/deploy-frontend.sh
```

This deploys:
- **VPC** - Network infrastructure with public/private subnets
- **ECS Fargate** - Container service for BFF server
- **Application Load Balancer** - Traffic distribution
- **CloudFront** - Global CDN for React app
- **Cognito** - User authentication

The script automatically:
- Builds React application
- Creates Docker image for BFF server
- Pushes to ECR and deploys to ECS
- Creates frontend-config.json with URLs

**Outputs:**
- CloudFront URL (application endpoint)
- Cognito User Pool ID
- ALB DNS name
- ECS cluster/service names

### 4. Deploy Tools

```bash
./terraform/deploy-tools.sh
```

This deploys:
- **AgentCore Gateway** - MCP protocol endpoint
- **Lambda Functions** - tool implementations
  - Tavily Search
  - Google Search
  - Wikipedia Search
  - ArXiv Search
  - Stock Tools (quotes, history, news, analysis)
- **Parameter Store** - Secure API key storage

### 5. Create Users (Optional)

Create a Cognito user:

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username user@example.com \
  --user-attributes Name=email,Value=user@example.com \
  --temporary-password 'TempPass123!' \
  --message-action SUPPRESS
```

Set permanent password:

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id <USER_POOL_ID> \
  --username user@example.com \
  --password 'YourPassword123!' \
  --permanent
```

### 6. Access Application

Navigate to the CloudFront URL from frontend deployment output:

```
https://<cloudfront-id>.cloudfront.net
```

Log in with your Cognito credentials.

## Configuration Files

### Environment Variables (.env)

Auto-populated by Terraform, but you can manually update:

```bash
python scripts/update_env.py
```

### Frontend Configuration (frontend-config.json)

Generated after frontend deployment with:
- API URL
- Cognito configuration
- AWS region

### Model Registry (shared/model_registry.json)

Configure available models and their combinations. See [MODEL_CONFIGURATION.md](./MODEL_CONFIGURATION.md).

## Updating Deployments

### Update Backend Code

```bash
# Edit code in research-agent/ or chat-agent/
./terraform/deploy-backend.sh
```

CodeBuild automatically rebuilds and redeploys containers.

### Update Frontend Code

```bash
# Edit code in frontend/
./terraform/deploy-frontend.sh
```

Rebuilds React app and Docker image, then updates ECS service.

### Update Tools

```bash
# Edit Lambda functions in terraform/tools/lambdas/
./terraform/deploy-tools.sh
```

Repackages and redeploys Lambda functions.

## Troubleshooting

### Backend deployment fails

- Check AWS credentials: `aws sts get-caller-identity`
- Verify region in `.env` matches AWS CLI config
- Check Terraform state: `cd terraform/backend && terraform state list`

### Frontend fails to load

- Wait 5-10 minutes for ECS tasks to start
- Check ECS service status in AWS Console
- Verify CloudFront distribution is deployed
- Check ALB target health

### Research fails

- Verify API keys in `.env` are correct
- Check DynamoDB table exists and is accessible
- Verify AgentCore Runtime status is READY
- Check CloudWatch logs for errors

### Image builds fail

- CodeBuild needs Docker image permissions
- Check CodeBuild logs in AWS Console
- Verify ECR repository exists

## Cleanup

To destroy all resources:

```bash
# Delete frontend
cd terraform/frontend
terraform destroy -auto-approve

# Delete tools
cd terraform/tools
terraform destroy -auto-approve

# Delete backend
cd terraform/backend
terraform destroy -auto-approve
```

**Warning:** This deletes all data including research outputs, user preferences, and memory.

## Architecture

```
┌─────────────────┐
│   CloudFront    │
│   (React App)   │
└────────┬────────┘
         │
    ┌────▼─────┐
    │   ALB    │
    └────┬─────┘
         │
    ┌────▼─────────┐
    │  ECS Fargate │
    │  (BFF Server)│
    └────┬─────────┘
         │
    ┌────▼──────────────────┐
    │  AgentCore Runtime    │
    │  ┌─────────────────┐  │
    │  │ Research Agent  │  │
    │  └─────────────────┘  │
    │  ┌─────────────────┐  │
    │  │   Chat Agent    │  │
    │  └─────────────────┘  │
    └───────┬───────────────┘
            │
    ┌───────▼────────────┐
    │  AgentCore Gateway │
    │  (14 Lambda Tools) │
    └────────────────────┘
            │
    ┌───────▼────────────┐
    │   AWS Services     │
    │  • DynamoDB        │
    │  • S3              │
    │  • Memory          │
    │  • CloudWatch      │
    └────────────────────┘
```

## Cost Estimation

Estimated monthly costs (us-west-2):

- **ECS Fargate** (0.25 vCPU, 0.5GB): ~$15
- **ALB**: ~$20
- **CloudFront**: $0 + data transfer
- **DynamoDB** (on-demand): ~$5
- **S3**: ~$1 per 1000 research reports
- **AgentCore Runtime**: Based on usage
- **Bedrock models**: Pay per token
- **Lambda**: Pay per invocation (~$0.20 per 1M)

**Total**: ~$50-100/month + model inference costs

## Security

- All traffic encrypted (HTTPS/TLS)
- Cognito manages authentication
- IAM roles follow least privilege
- API keys stored in Parameter Store
- VPC isolates backend resources
- Security groups restrict access

## Support

For issues or questions:
- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- Review CloudWatch logs
- Open GitHub issue
