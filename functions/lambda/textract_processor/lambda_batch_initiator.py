import boto3
import json
from datetime import datetime
import config

textract_client = boto3.client('textract', region_name=config.AWS_REGION)
s3_client = boto3.client('s3', region_name=config.AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)

def lambda_handler(event, context):
    """
    Initiates Textract processing for all PDFs in a batch folder.

    Event format:
    {
        "bucket_name": "your-source-bucket",  # Optional, uses config.SOURCE_BUCKET if not provided
        "batch_prefix": "batch-1/",
        "sns_topic_arn": "arn:aws:sns:us-east-1:ACCOUNT_ID:textract-completion-topic",
        "textract_role_arn": "arn:aws:iam::ACCOUNT_ID:role/textract-sns-role"
    }
    """
    bucket_name = event.get('bucket_name', config.SOURCE_BUCKET)
    batch_prefix = event['batch_prefix']
    sns_topic_arn = event['sns_topic_arn']
    role_arn = event['textract_role_arn']

    print(f"Processing batch: {batch_prefix}")

    # List all PDFs in the batch folder
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=bucket_name,
        Prefix=batch_prefix
    )

    pdf_files = []
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.pdf'):
                pdf_files.append(obj['Key'])

    print(f"Found {len(pdf_files)} PDF files")

    jobs_started = []
    jobs_failed = []

    for pdf_key in pdf_files:
        try:
            # Start asynchronous document analysis
            response = textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': pdf_key
                    }
                },
                FeatureTypes=config.FEATURE_TYPES,  # Extract key-value pairs + tables
                NotificationChannel={
                    'SNSTopicArn': sns_topic_arn,
                    'RoleArn': role_arn
                }
            )

            job_id = response['JobId']

            # Store job mapping in DynamoDB for tracking
            table.put_item(Item={
                'JobId': job_id,
                'SourceKey': pdf_key,
                'Bucket': bucket_name,
                'BatchPrefix': batch_prefix,
                'Status': 'IN_PROGRESS',
                'StartTime': datetime.utcnow().isoformat()
            })

            jobs_started.append({
                'pdf': pdf_key,
                'job_id': job_id
            })

            print(f"Started job {job_id} for {pdf_key}")

        except Exception as e:
            error_msg = f"Error processing {pdf_key}: {str(e)}"
            print(error_msg)
            jobs_failed.append({
                'pdf': pdf_key,
                'error': str(e)
            })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Started {len(jobs_started)} Textract jobs',
            'batch': batch_prefix,
            'jobs_started': len(jobs_started),
            'jobs_failed': len(jobs_failed),
            'failed_jobs': jobs_failed
        })
    }
