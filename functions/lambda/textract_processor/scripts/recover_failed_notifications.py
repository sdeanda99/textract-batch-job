#!/usr/bin/env python3
"""
Recovery script to process Textract jobs that completed but notifications failed.
Finds IN_PROGRESS jobs in DynamoDB, checks if they succeeded in Textract,
and processes them manually.
"""

import boto3
import json
from datetime import datetime

# AWS clients
textract = boto3.client('textract', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('textract-jobs')

def parse_textract_response(blocks):
    """Extract data from Textract blocks"""
    extracted = {
        'raw_text': [],
        'key_value_pairs': [],
        'tables': []
    }

    block_map = {block['Id']: block for block in blocks}

    for block in blocks:
        if block['BlockType'] == 'LINE':
            extracted['raw_text'].append({
                'text': block['Text'],
                'confidence': block['Confidence']
            })
        elif block['BlockType'] == 'KEY_VALUE_SET':
            if 'KEY' in block.get('EntityTypes', []):
                key_text = get_text_from_relationship(block, block_map)
                value_block = get_value_block(block, block_map)
                value_text = get_text_from_relationship(value_block, block_map) if value_block else ''

                extracted['key_value_pairs'].append({
                    'key': key_text,
                    'value': value_text,
                    'confidence': block['Confidence']
                })

    return extracted

def get_text_from_relationship(block, block_map):
    """Helper to extract text from CHILD relationships"""
    if not block:
        return ''
    text = ''
    if 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child = block_map.get(child_id)
                    if child and child['BlockType'] == 'WORD':
                        text += child['Text'] + ' '
    return text.strip()

def get_value_block(key_block, block_map):
    """Helper to find VALUE block for a KEY"""
    if 'Relationships' in key_block:
        for relationship in key_block['Relationships']:
            if relationship['Type'] == 'VALUE':
                for value_id in relationship['Ids']:
                    return block_map.get(value_id)
    return None

def recover_job(job_data):
    """Attempt to recover a single job"""
    job_id = job_data['JobId']

    try:
        # Check Textract status
        print(f"  Checking job {job_id[:16]}...")
        result = textract.get_document_analysis(JobId=job_id)

        status = result['JobStatus']

        if status != 'SUCCEEDED':
            print(f"    Status: {status} - Skipping")
            return False

        print(f"    Status: SUCCEEDED - Recovering...")

        # Get all blocks (handle pagination)
        blocks = result['Blocks']
        while 'NextToken' in result:
            result = textract.get_document_analysis(
                JobId=job_id,
                NextToken=result['NextToken']
            )
            blocks.extend(result['Blocks'])

        # Parse data
        extracted_data = parse_textract_response(blocks)

        # Add metadata
        extracted_data['metadata'] = {
            'source_file': job_data['SourceKey'],
            'bucket': job_data['Bucket'],
            'batch': job_data['BatchPrefix'],
            'job_id': job_id,
            'processed_time': datetime.utcnow().isoformat(),
            'total_blocks': len(blocks),
            'recovered': True
        }

        # Save to S3
        filename = job_data['SourceKey'].split('/')[-1].replace('.pdf', '.json')
        output_key = f"processed/{job_data['BatchPrefix']}{filename}"

        s3.put_object(
            Bucket=job_data['Bucket'],
            Key=output_key,
            Body=json.dumps(extracted_data, indent=2),
            ContentType='application/json'
        )

        # Update DynamoDB
        table.update_item(
            Key={'JobId': job_id},
            UpdateExpression='SET #status = :status, OutputKey = :output, CompletedTime = :time',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': 'COMPLETED',
                ':output': output_key,
                ':time': datetime.utcnow().isoformat()
            }
        )

        print(f"    ✓ Recovered: {output_key}")
        return True

    except textract.exceptions.InvalidJobIdException:
        print(f"    Job expired (>7 days) - Cannot recover")
        # Mark as FAILED in DynamoDB
        table.update_item(
            Key={'JobId': job_id},
            UpdateExpression='SET #status = :status',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={':status': 'FAILED_EXPIRED'}
        )
        return False
    except Exception as e:
        print(f"    Error: {e}")
        return False

def main():
    print("=" * 70)
    print("Textract Job Recovery")
    print("=" * 70)
    print()

    # Scan for IN_PROGRESS jobs
    print("Scanning DynamoDB for IN_PROGRESS jobs...")
    response = table.scan(
        FilterExpression='#s = :status',
        ExpressionAttributeNames={'#s': 'Status'},
        ExpressionAttributeValues={':status': 'IN_PROGRESS'}
    )

    jobs = response['Items']

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#s = :status',
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={':status': 'IN_PROGRESS'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        jobs.extend(response['Items'])

    print(f"Found {len(jobs)} IN_PROGRESS jobs")
    print()

    if not jobs:
        print("No jobs to recover!")
        return

    # Ask for confirmation
    response = input(f"Attempt to recover {len(jobs)} jobs? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return

    print()
    print("Starting recovery...")
    print()

    recovered = 0
    failed = 0

    for idx, job_data in enumerate(jobs, 1):
        print(f"[{idx}/{len(jobs)}] Processing...")
        if recover_job(job_data):
            recovered += 1
        else:
            failed += 1

        # Progress update every 50 jobs
        if idx % 50 == 0:
            print(f"\n  Progress: {idx}/{len(jobs)} | Recovered: {recovered} | Failed: {failed}\n")

    print()
    print("=" * 70)
    print("Recovery Complete!")
    print("=" * 70)
    print(f"  Recovered: {recovered}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(jobs)}")
    print()

if __name__ == '__main__':
    main()
