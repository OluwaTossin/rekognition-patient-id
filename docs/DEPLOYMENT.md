# Deployment Guide

## Prerequisites

### AWS Account Setup
1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. IAM user with required permissions:
   - Lambda full access
   - DynamoDB full access
   - Rekognition full access
   - API Gateway full access
   - CloudWatch Logs full access

### Local Environment
```bash
# Install required tools
pip install awscli boto3

# Configure AWS credentials
aws configure
```

## Automated Deployment

### Using the Deploy Script
```bash
# Make script executable
chmod +x scripts/deploy.sh

# Set environment variables (optional)
export AWS_REGION=us-east-1
export COLLECTION_ID=my-patient-faces
export TABLE_NAME=my_patients

# Run deployment
./scripts/deploy.sh
```

## Manual Deployment

### Step 1: Create Rekognition Collection
```bash
aws rekognition create-collection \
  --collection-id cmc-patient-faces \
  --region us-east-1
```

### Step 2: Create DynamoDB Table
```bash
aws dynamodb create-table \
  --table-name cmc_patients \
  --attribute-definitions \
    AttributeName=patient_id,AttributeType=S \
    AttributeName=face_id,AttributeType=S \
  --key-schema \
    AttributeName=patient_id,KeyType=HASH \
  --global-secondary-indexes \
    'IndexName=face_id-index,KeySchema=[{AttributeName=face_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' \
  --provisioned-throughput \
    ReadCapacityUnits=5,WriteCapacityUnits=5
```

### Step 3: Create IAM Role
```bash
# Create role
aws iam create-role \
  --role-name lambda-rekognition-role \
  --assume-role-policy-document file://lambda-trust.json

# Attach policy
aws iam put-role-policy \
  --role-name lambda-rekognition-role \
  --policy-name LambdaRekognitionPolicy \
  --policy-document file://lambda-policy.json
```

### Step 4: Deploy Lambda Functions
```bash
# Get account ID for role ARN
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/lambda-rekognition-role"

# Package register function
cd build-register
zip -r register_patient.zip register_patient.py
aws lambda create-function \
  --function-name register-patient \
  --runtime python3.9 \
  --role "$ROLE_ARN" \
  --handler register_patient.handler \
  --zip-file fileb://register_patient.zip \
  --environment Variables='{COLLECTION_ID=cmc-patient-faces,TABLE_NAME=cmc_patients}'

# Package identify function
cd ../build-identify
zip -r identify_patient.zip identify_patient.py
aws lambda create-function \
  --function-name identify-patient \
  --runtime python3.9 \
  --role "$ROLE_ARN" \
  --handler identify_patient.handler \
  --zip-file fileb://identify_patient.zip \
  --environment Variables='{COLLECTION_ID=cmc-patient-faces,TABLE_NAME=cmc_patients,MATCH_THRESHOLD=95}'
```

### Step 5: Create API Gateway
```bash
# Create REST API
API_ID=$(aws apigateway create-rest-api \
  --name patient-identity-api \
  --description "Patient Identity Verification API" \
  --query 'id' --output text)

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[0].id' --output text)

# Create 'patients' resource
PATIENTS_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part patients \
  --query 'id' --output text)

# Create 'register' resource
REGISTER_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PATIENTS_ID \
  --path-part register \
  --query 'id' --output text)

# Create 'identify' resource
IDENTIFY_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PATIENTS_ID \
  --path-part identify \
  --query 'id' --output text)

# Add POST methods and integrations
# (Additional commands for methods, integrations, and deployment)
```

## Environment-Specific Deployments

### Development
```bash
export ENVIRONMENT=dev
export COLLECTION_ID=patient-faces-dev
export TABLE_NAME=cmc_patients_dev
./scripts/deploy.sh
```

### Production
```bash
export ENVIRONMENT=prod
export COLLECTION_ID=patient-faces-prod
export TABLE_NAME=cmc_patients_prod
./scripts/deploy.sh
```

## Verification

### Test Deployment
```bash
# Run test script
chmod +x scripts/test.sh
./scripts/test.sh

# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/

# Verify DynamoDB table
aws dynamodb describe-table --table-name cmc_patients

# Check Rekognition collection
aws rekognition describe-collection --collection-id cmc-patient-faces
```

## Troubleshooting

### Common Issues
1. **Permission Errors**: Ensure IAM role has correct policies
2. **Resource Already Exists**: Use `--no-fail-on-empty-changeset` for CloudFormation
3. **Region Mismatch**: Ensure all resources are in the same region
4. **API Gateway Integration**: Verify Lambda permissions for API Gateway

### Cleanup
```bash
# Delete Lambda functions
aws lambda delete-function --function-name register-patient
aws lambda delete-function --function-name identify-patient

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id YOUR_API_ID

# Delete DynamoDB table
aws dynamodb delete-table --table-name cmc_patients

# Delete Rekognition collection
aws rekognition delete-collection --collection-id cmc-patient-faces

# Delete IAM role
aws iam delete-role-policy --role-name lambda-rekognition-role --policy-name LambdaRekognitionPolicy
aws iam delete-role --role-name lambda-rekognition-role
```