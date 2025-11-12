#!/bin/bash

set -e

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please copy .env.example to .env and configure your settings:"
    echo "  cp $SCRIPT_DIR/.env.example $ENV_FILE"
    exit 1
fi

# Export variables from .env
set -a
source "$ENV_FILE"
set +a

# Configuration from environment variables
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME}"
SOURCE_BUCKET="${SOURCE_BUCKET}"
ROLE_NAME="${LAMBDA_ROLE_NAME}"
REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"
TIMEOUT="${LAMBDA_TIMEOUT:-900}"
MEMORY="${LAMBDA_MEMORY:-1024}"

echo "====================================================================="
echo "S3 Bucket Creator Lambda Deployment"
echo "====================================================================="
echo ""

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Step 1: Create IAM role if it doesn't exist
echo "Step 1: Checking/Creating IAM role..."
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --profile $AWS_PROFILE --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    echo "Creating IAM role: $ROLE_NAME"

    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create role
    ROLE_ARN=$(aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --profile $AWS_PROFILE \
        --query 'Role.Arn' \
        --output text)

    echo "Created role: $ROLE_ARN"

    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
        --profile $AWS_PROFILE

    # Create and attach S3 full access policy (needed to create buckets)
    cat > /tmp/s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name S3FullAccess \
        --policy-document file:///tmp/s3-policy.json \
        --profile $AWS_PROFILE

    echo "Attached policies to role"
    echo "Waiting 10 seconds for role to propagate..."
    sleep 10
else
    echo "IAM role already exists: $ROLE_ARN"
fi

echo ""

# Step 2: Package Lambda function
echo "Step 2: Packaging Lambda function..."
zip -q lambda_function.zip lambda_bucket_creator.py config.py
echo "Lambda function packaged (includes config.py)"
echo ""

# Step 3: Check if Lambda function exists
echo "Step 3: Deploying Lambda function..."
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --profile $AWS_PROFILE 2>/dev/null || echo "")

if [ -z "$FUNCTION_EXISTS" ]; then
    echo "Creating new Lambda function: $FUNCTION_NAME"
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.12 \
        --role $ROLE_ARN \
        --handler lambda_bucket_creator.lambda_handler \
        --zip-file fileb://lambda_function.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --environment "Variables={SOURCE_BUCKET=$SOURCE_BUCKET,AWS_REGION=$REGION,BATCH_SIZE=$BATCH_SIZE}" \
        --profile $AWS_PROFILE \
        --region $REGION \
        --no-cli-pager
    echo "Lambda function created"
    echo "Waiting 15 seconds for Lambda to be ready..."
    sleep 15
else
    echo "Updating existing Lambda function: $FUNCTION_NAME"
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_function.zip \
        --profile $AWS_PROFILE \
        --region $REGION \
        --no-cli-pager

    echo "Updating Lambda environment variables..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables={SOURCE_BUCKET=$SOURCE_BUCKET,AWS_REGION=$REGION,BATCH_SIZE=$BATCH_SIZE}" \
        --profile $AWS_PROFILE \
        --region $REGION \
        --no-cli-pager

    echo "Lambda function updated"
    echo "Waiting 5 seconds..."
    sleep 5
fi

echo ""

# Step 4: Invoke Lambda function
echo "Step 4: Invoking Lambda function..."
echo "This will create new S3 buckets for each batch folder"
echo ""

aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload "{\"source_bucket\": \"$SOURCE_BUCKET\", \"region\": \"$REGION\"}" \
    --profile $AWS_PROFILE \
    --region $REGION \
    --cli-binary-format raw-in-base64-out \
    /tmp/lambda-response.json \
    --no-cli-pager

echo ""
echo "====================================================================="
echo "Lambda Response:"
echo "====================================================================="
cat /tmp/lambda-response.json | python3 -m json.tool
echo ""

# Cleanup
rm -f lambda_function.zip
rm -f /tmp/trust-policy.json
rm -f /tmp/s3-policy.json

echo ""
echo "====================================================================="
echo "✓ Deployment Complete!"
echo "====================================================================="
echo ""
echo "To view all created buckets, run:"
echo "aws s3 ls --profile $AWS_PROFILE | grep batch-"
