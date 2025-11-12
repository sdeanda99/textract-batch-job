import boto3
import json
from typing import List, Dict
import config

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda function to organize PDFs in S3 bucket into batches of 150 files each.
    Configuration can be overridden via event payload or set via environment variables.
    """
    bucket_name = event.get('bucket_name', config.SOURCE_BUCKET)
    batch_size = event.get('batch_size', config.BATCH_SIZE)

    print(f"Starting PDF organization for bucket: {bucket_name}")
    print(f"Batch size: {batch_size}")

    try:
        # List all PDF files in the bucket
        pdf_files = []
        paginator = s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Only include PDF files that are NOT already in batch folders
                    if key.endswith('.pdf') and not key.startswith('batch-'):
                        pdf_files.append(key)

        total_files = len(pdf_files)
        print(f"Found {total_files} PDF files to organize")

        if total_files == 0:
            return {
                'statusCode': 200,
                'body': json.dumps('No PDF files found to organize')
            }

        # Calculate number of batches
        total_batches = (total_files + batch_size - 1) // batch_size
        print(f"Will create {total_batches} batches")

        # Organize files into batches
        copied_count = 0
        for idx, file_key in enumerate(pdf_files):
            batch_num = (idx // batch_size) + 1

            # Get just the filename
            filename = file_key.split('/')[-1]

            # Define new key in batch folder
            new_key = f"batch-{batch_num}/{filename}"

            # Copy file to batch folder
            copy_source = {'Bucket': bucket_name, 'Key': file_key}
            s3_client.copy_object(
                CopySource=copy_source,
                Bucket=bucket_name,
                Key=new_key
            )

            copied_count += 1

            # Log progress every 100 files
            if copied_count % 100 == 0:
                print(f"Progress: {copied_count}/{total_files} files copied")

        print(f"Successfully organized {copied_count} files into {total_batches} batches")

        # Get summary of batches
        batch_summary = {}
        for batch_num in range(1, total_batches + 1):
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=f"batch-{batch_num}/"
            )
            count = len(response.get('Contents', [])) - 1  # Subtract 1 for the folder itself if counted
            batch_summary[f"batch-{batch_num}"] = count

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'PDF organization completed successfully',
                'total_files': total_files,
                'total_batches': total_batches,
                'batch_summary': batch_summary
            }, indent=2)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
