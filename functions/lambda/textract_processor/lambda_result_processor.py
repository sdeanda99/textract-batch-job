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
    Triggered by SQS messages from SNS topic.
    Retrieves Textract results and saves to S3.
    """
    processed_count = 0
    failed_count = 0

    for record in event['Records']:
        try:
            # Parse SNS message from SQS
            sns_message = json.loads(record['body'])
            message = json.loads(sns_message['Message'])

            job_id = message['JobId']
            status = message['Status']

            print(f"Processing job {job_id} with status: {status}")

            if status != 'SUCCEEDED':
                print(f"Job {job_id} failed with status: {status}")
                # Update DynamoDB to mark as failed
                table.update_item(
                    Key={'JobId': job_id},
                    UpdateExpression='SET #status = :status, CompletedTime = :time',
                    ExpressionAttributeNames={'#status': 'Status'},
                    ExpressionAttributeValues={
                        ':status': f'FAILED_{status}',
                        ':time': datetime.utcnow().isoformat()
                    }
                )
                failed_count += 1
                continue

            # Get job details from DynamoDB
            response = table.get_item(Key={'JobId': job_id})

            if 'Item' not in response:
                print(f"Job {job_id} not found in DynamoDB")
                failed_count += 1
                continue

            job_data = response['Item']

            # Retrieve Textract results with pagination
            blocks = []
            next_token = None

            while True:
                if next_token:
                    result = textract_client.get_document_analysis(
                        JobId=job_id,
                        NextToken=next_token
                    )
                else:
                    result = textract_client.get_document_analysis(JobId=job_id)

                blocks.extend(result['Blocks'])

                if 'NextToken' in result:
                    next_token = result['NextToken']
                else:
                    break

            print(f"Retrieved {len(blocks)} blocks for job {job_id}")

            # Parse key-value pairs and text
            extracted_data = parse_textract_response(blocks)

            # Add metadata
            extracted_data['metadata'] = {
                'source_file': job_data['SourceKey'],
                'bucket': job_data['Bucket'],
                'batch': job_data['BatchPrefix'],
                'job_id': job_id,
                'processed_time': datetime.utcnow().isoformat(),
                'total_blocks': len(blocks)
            }

            # Save to S3 using config for output location
            filename = job_data['SourceKey'].split('/')[-1].replace('.pdf', '.json')
            output_key = config.get_output_key(job_data['BatchPrefix'], filename)

            # Use OUTPUT_BUCKET from config (can be different from source bucket)
            output_bucket = config.OUTPUT_BUCKET

            s3_client.put_object(
                Bucket=output_bucket,
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

            print(f"Successfully processed {job_data['SourceKey']} -> {output_key}")
            processed_count += 1

        except Exception as e:
            print(f"Error processing record: {str(e)}")
            failed_count += 1

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'failed': failed_count
        })
    }


def parse_textract_response(blocks):
    """
    Extracts raw text, key-value pairs, and tables from Textract blocks.
    """
    extracted = {
        'raw_text': [],
        'key_value_pairs': [],
        'tables': []
    }

    # Build block map for relationships
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

        elif block['BlockType'] == 'TABLE':
            table_data = extract_table(block, block_map)
            if table_data:
                extracted['tables'].append(table_data)

    return extracted


def get_text_from_relationship(block, block_map):
    """Helper to extract text from CHILD relationships."""
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
    """Helper to find VALUE block for a KEY."""
    if 'Relationships' in key_block:
        for relationship in key_block['Relationships']:
            if relationship['Type'] == 'VALUE':
                for value_id in relationship['Ids']:
                    return block_map.get(value_id)
    return None


def extract_table(table_block, block_map):
    """Extract table structure with rows and cells."""
    table_data = {
        'rows': [],
        'confidence': table_block.get('Confidence', 0)
    }

    if 'Relationships' not in table_block:
        return None

    # Get all CELL blocks
    cells = {}
    for relationship in table_block['Relationships']:
        if relationship['Type'] == 'CHILD':
            for cell_id in relationship['Ids']:
                cell_block = block_map.get(cell_id)
                if cell_block and cell_block['BlockType'] == 'CELL':
                    row_index = cell_block.get('RowIndex', 0)
                    col_index = cell_block.get('ColumnIndex', 0)
                    cell_text = get_text_from_relationship(cell_block, block_map)

                    if row_index not in cells:
                        cells[row_index] = {}
                    cells[row_index][col_index] = cell_text

    # Convert to structured rows
    for row_idx in sorted(cells.keys()):
        row_data = []
        for col_idx in sorted(cells[row_idx].keys()):
            row_data.append(cells[row_idx][col_idx])
        table_data['rows'].append(row_data)

    return table_data if table_data['rows'] else None
