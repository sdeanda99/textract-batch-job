import boto3
import json
import time
import random
import string
from datetime import datetime
import config

s3_client = boto3.client('s3')

def generate_random_chars(length=6):
    """Generate random alphanumeric characters"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def lambda_handler(event, context):
    """
    Lambda function to create new S3 buckets for each batch folder.
    Each bucket will be named: batch-{N}-{timestamp}-{random6chars}
    Configuration can be overridden via event payload or set via environment variables.
    """
    source_bucket = event.get('source_bucket', config.SOURCE_BUCKET)
    region = event.get('region', config.AWS_REGION)

    print(f"Starting bucket creation process for source bucket: {source_bucket}")

    try:
        # List all batch folders in the source bucket
        paginator = s3_client.get_paginator('list_objects_v2')
        batch_folders = set()

        for page in paginator.paginate(Bucket=source_bucket, Delimiter='/'):
            if 'CommonPrefixes' in page:
                for prefix in page['CommonPrefixes']:
                    folder_name = prefix['Prefix'].rstrip('/')
                    if folder_name.startswith('batch-'):
                        batch_folders.add(folder_name)

        batch_folders = sorted(batch_folders, key=lambda x: int(x.split('-')[1]))
        print(f"Found {len(batch_folders)} batch folders: {batch_folders}")

        if not batch_folders:
            return {
                'statusCode': 404,
                'body': json.dumps('No batch folders found in source bucket')
            }

        created_buckets = []
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        # Create a new bucket for each batch folder
        for batch_folder in batch_folders:
            # Extract batch number (e.g., "batch-1" -> "1")
            batch_num = batch_folder.split('-')[1]
            random_suffix = generate_random_chars(6)

            # Create bucket name: batch-1-20251106235959-abc123
            new_bucket_name = f"batch-{batch_num}-{timestamp}-{random_suffix}"

            print(f"Creating bucket: {new_bucket_name}")

            # Create the bucket
            if region == 'us-east-1':
                s3_client.create_bucket(Bucket=new_bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=new_bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )

            # Copy all files from batch folder to new bucket
            print(f"Copying files from {batch_folder}/ to {new_bucket_name}")
            copied_count = 0

            for page in paginator.paginate(Bucket=source_bucket, Prefix=f"{batch_folder}/"):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        source_key = obj['Key']

                        # Skip the folder itself if it appears as an object
                        if source_key.endswith('/'):
                            continue

                        # Get just the filename (without the batch folder prefix)
                        filename = source_key.split('/')[-1]

                        # Copy to new bucket (files at root level)
                        copy_source = {'Bucket': source_bucket, 'Key': source_key}
                        s3_client.copy_object(
                            CopySource=copy_source,
                            Bucket=new_bucket_name,
                            Key=filename
                        )
                        copied_count += 1

            print(f"Copied {copied_count} files to {new_bucket_name}")

            created_buckets.append({
                'batch_folder': batch_folder,
                'new_bucket': new_bucket_name,
                'files_copied': copied_count
            })

        print(f"Successfully created {len(created_buckets)} buckets")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Bucket creation completed successfully',
                'total_buckets_created': len(created_buckets),
                'buckets': created_buckets
            }, indent=2)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
