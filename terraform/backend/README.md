# Deep Research Agent - Terraform Infrastructure

This directory contains Terraform configurations for deploying the Deep Research Agent infrastructure on AWS.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AWS Infrastructure                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────┐      ┌──────────────────────┐     │
│  │ ECR Repository  │─────▶│ AgentCore Runtime    │     │
│  │  (Docker Image) │      │  (Research Workflow) │     │
│  └─────────────────┘      └──────────┬───────────┘     │
│                                       │                  │
│                            ┌──────────┴──────────┐      │
│                            │                     │      │
│                  ┌─────────▼────────┐  ┌────────▼──┐   │
│                  │ DynamoDB Tables  │  │ S3 Bucket │   │
│                  │  - Sessions      │  │ (Reports) │   │
│                  │  - Status        │  └───────────┘   │
│                  └──────────────────┘                   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Resources Created

1. **ECR Repository** - Stores Docker image for AgentCore Runtime
2. **AgentCore Runtime** - Executes research workflow
3. **DynamoDB Tables**:
   - `sessions` - Research session metadata
   - `research_status` - Real-time research progress tracking
4. **S3 Bucket** - Research outputs (reports, documents)
5. **IAM Role & Policies** - AgentCore Runtime permissions

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- Docker (for building and pushing images)

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Configure Variables

Copy the example variables file and customize:

```bash
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

### 3. Plan Deployment

```bash
terraform plan
```

### 4. Deploy Infrastructure

```bash
terraform apply
```

### 5. Build and Push Docker Image

After infrastructure is deployed, build and push the Docker image:

```bash
# Get ECR repository URL from Terraform output
ECR_REPO=$(terraform output -raw ecr_repository_url)

# Login to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin $ECR_REPO

# Build Docker image (from project root)
cd ..
docker build -t deep-research-agent -f docker/Dockerfile.agentcore .

# Tag and push
docker tag deep-research-agent:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
```

### 6. Update AgentCore Runtime

After pushing the image, the AgentCore Runtime will automatically use the new image.

## Outputs

After deployment, Terraform will output:

- `ecr_repository_url` - ECR repository URL for Docker images
- `agent_runtime_id` - AgentCore Runtime ID
- `agent_runtime_arn` - AgentCore Runtime ARN
- `dynamodb_sessions_table` - DynamoDB sessions table name
- `dynamodb_status_table` - DynamoDB status table name
- `s3_outputs_bucket` - S3 bucket for research outputs

Use these values to configure your BFF server environment variables.

## Configuration

### Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region for deployment | `us-west-2` |
| `environment` | Environment name (dev/staging/prod) | `dev` |
| `agentcore_memory_id` | AgentCore Memory ID | `ResearchMemory-2OeNa02agH` |
| `log_level` | Application log level | `INFO` |
| `enable_xray` | Enable AWS X-Ray tracing | `false` |

### Environment Variables (AgentCore Runtime)

The following environment variables are automatically configured for the AgentCore Runtime:

- `AWS_REGION` - AWS region
- `DYNAMODB_SESSIONS_TABLE` - Sessions table name
- `DYNAMODB_STATUS_TABLE` - Status table name
- `S3_OUTPUTS_BUCKET` - S3 bucket name
- `AGENTCORE_MEMORY_ID` - Memory ID for persistent context
- `LOG_LEVEL` - Logging level
- `ENABLE_XRAY` - X-Ray tracing flag

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will permanently delete all resources including DynamoDB tables and S3 bucket contents.

## Cost Estimation

Estimated monthly costs (us-west-2):

- AgentCore Runtime: ~$XX/month (based on usage)
- DynamoDB (Pay-per-request): ~$X/month (low usage)
- S3 Storage: ~$X/month (first 90 days)
- ECR: ~$X/month (< 10 images)

**Total**: ~$XX-XXX/month depending on usage

## Troubleshooting

### Issue: AgentCore Runtime fails to start

Check CloudWatch Logs:
```bash
aws logs tail /aws/bedrock-agentcore/deep-research-agent --follow
```

### Issue: Permission denied errors

Verify IAM role permissions:
```bash
terraform output agent_runtime_role_arn
aws iam get-role --role-name <role-name>
```

### Issue: Container image not found

Ensure Docker image is pushed to ECR:
```bash
aws ecr describe-images --repository-name <repo-name>
```

## Next Steps

After deploying the infrastructure:

1. Configure BFF server with Terraform outputs
2. Test research workflow invocation
3. Monitor CloudWatch Logs and DynamoDB tables
4. Set up CloudWatch alarms for monitoring

## Support

For issues or questions, see the main project README.
