#!/bin/bash
# deployment script for the Patient Identity Verification System

set -e

echo "🚀 Deploying Patient Identity Verification System..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Set default region if not set
AWS_REGION=${AWS_REGION:-us-east-1}
COLLECTION_ID=${COLLECTION_ID:-cmc-patient-faces}
TABLE_NAME=${TABLE_NAME:-cmc_patients}

echo "📋 Configuration:"
echo "  - AWS Region: $AWS_REGION"
echo "  - Collection ID: $COLLECTION_ID"
echo "  - Table Name: $TABLE_NAME"

# Step 1: Create Rekognition Collection
echo "🔍 Creating Rekognition collection..."
aws rekognition create-collection \
  --collection-id "$COLLECTION_ID" \
  --region "$AWS_REGION" 2>/dev/null || echo "Collection already exists"

# Step 2: Create DynamoDB Table
echo "🗄️  Creating DynamoDB table..."
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=patient_id,AttributeType=S \
    AttributeName=face_id,AttributeType=S \
  --key-schema \
    AttributeName=patient_id,KeyType=HASH \
  --global-secondary-indexes \
    'IndexName=face_id-index,KeySchema=[{AttributeName=face_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' \
  --provisioned-throughput \
    ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region "$AWS_REGION" 2>/dev/null || echo "Table already exists"

# Step 3: Create IAM Role
echo "🔐 Creating IAM role..."
ROLE_NAME="lambda-rekognition-role"

# Create role
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file://lambda-trust.json 2>/dev/null || echo "Role already exists"

# Attach policy
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name LambdaRekognitionPolicy \
  --policy-document file://lambda-policy.json

# Get account ID for ARN construction
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

# Wait for role to be ready
echo "⏳ Waiting for IAM role to be ready..."
sleep 10

# Step 4: Package and Deploy Lambda Functions
echo "📦 Packaging Lambda functions..."

# Package register function
cd build-register
zip -r register_patient.zip register_patient.py
cd ..

# Package identify function
cd build-identify
zip -r identify_patient.zip identify_patient.py
cd ..

# Deploy register function
echo "🚀 Deploying register function..."
aws lambda create-function \
  --function-name register-patient \
  --runtime python3.9 \
  --role "$ROLE_ARN" \
  --handler register_patient.handler \
  --zip-file fileb://build-register/register_patient.zip \
  --environment "Variables={COLLECTION_ID=$COLLECTION_ID,TABLE_NAME=$TABLE_NAME}" \
  --timeout 30 \
  --region "$AWS_REGION" 2>/dev/null || \
aws lambda update-function-code \
  --function-name register-patient \
  --zip-file fileb://build-register/register_patient.zip \
  --region "$AWS_REGION"

# Deploy identify function
echo "🔎 Deploying identify function..."
aws lambda create-function \
  --function-name identify-patient \
  --runtime python3.9 \
  --role "$ROLE_ARN" \
  --handler identify_patient.handler \
  --zip-file fileb://build-identify/identify_patient.zip \
  --environment "Variables={COLLECTION_ID=$COLLECTION_ID,TABLE_NAME=$TABLE_NAME,MATCH_THRESHOLD=95}" \
  --timeout 30 \
  --region "$AWS_REGION" 2>/dev/null || \
aws lambda update-function-code \
  --function-name identify-patient \
  --zip-file fileb://build-identify/identify_patient.zip \
  --region "$AWS_REGION"

# Step 5: Create API Gateway (Basic setup)
echo "🌐 Setting up API Gateway..."
API_NAME="patient-identity-api"

# Create API
API_ID=$(aws apigateway create-rest-api \
  --name "$API_NAME" \
  --description "Patient Identity Verification API" \
  --region "$AWS_REGION" \
  --query 'id' --output text 2>/dev/null || \
aws apigateway get-rest-apis \
  --query "items[?name=='$API_NAME'].id" \
  --output text --region "$AWS_REGION")

echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Summary:"
echo "  - Rekognition Collection: $COLLECTION_ID"
echo "  - DynamoDB Table: $TABLE_NAME"
echo "  - Lambda Functions: register-patient, identify-patient"
echo "  - API Gateway ID: $API_ID"
echo ""
echo "🧪 Test your deployment:"
echo "  - Check Lambda functions in AWS Console"
echo "  - Test with sample images: patient1.jpg"
echo "  - Monitor logs in CloudWatch"
echo ""
echo "📚 Next steps:"
echo "  - Configure API Gateway routes manually or use AWS Console"
echo "  - Set up monitoring and alarms"
echo "  - Test with real patient data"