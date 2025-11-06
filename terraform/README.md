# Terraform Infrastructure

This directory contains all infrastructure-as-code for the Deep Research Agent project.

## Directory Structure

```
terraform/
├── backend/              # Backend infrastructure (AgentCore, DynamoDB, S3, ECR)
├── frontend/             # Frontend infrastructure (ECS, ALB, CloudFront, Cognito)
├── tools/                # Lambda tools and Gateway infrastructure
├── deploy-backend.sh     # Backend deployment script
├── deploy-frontend.sh    # Frontend deployment script
└── deploy-tools.sh       # Tools deployment script
```

## Deployment

From the project root, run:

```bash
./deploy.sh
```

This will present an interactive menu to deploy:
1. Backend only
2. Frontend only
3. Tools only
4. Full Stack (Backend + Frontend)
5. Everything (Backend + Frontend + Tools)

## Individual Deployments

You can also deploy individual stacks directly:

```bash
# Backend
cd terraform
./deploy-backend.sh

# Frontend
cd terraform
./deploy-frontend.sh

# Tools
cd terraform
./deploy-tools.sh
```

## Prerequisites

- AWS CLI configured
- Terraform installed
- Docker installed (for frontend deployment)
- `.env` file in project root with required API keys
