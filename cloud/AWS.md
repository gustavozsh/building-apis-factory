# AWS Deployment Configurations

## AWS ECS (Elastic Container Service)

### Prerequisites
- AWS CLI installed and configured
- ECR repository created
- ECS cluster created

### Build and Push Docker Image
```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t building-apis-factory .

# Tag image
docker tag building-apis-factory:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/building-apis-factory:latest

# Push image
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/building-apis-factory:latest
```

### ECS Task Definition
See `ecs-task-definition.json` for the complete task definition.

## AWS Lambda with API Gateway

For serverless deployment, use AWS Lambda with API Gateway:

```bash
# Install AWS Lambda adapter
pip install mangum

# Deploy using AWS SAM or Serverless Framework
```

See `lambda-handler.py` for Lambda implementation.

## AWS EC2

Standard deployment on EC2:
1. Launch EC2 instance
2. Install Docker
3. Pull and run the container
4. Configure security groups for port 8000

## Environment Variables

Set these in your AWS environment:
- `ENV`: production
- Add any additional environment variables as needed
