"""
Configuration module for AWS Textract Processor.
Reads configuration from environment variables with sensible defaults.
"""
import os

# ============================================================================
# S3 Configuration
# ============================================================================
# Input bucket where PDFs are stored
SOURCE_BUCKET = os.environ.get('SOURCE_BUCKET', 'important-stuff-20251106-0-018ql4')

# Output bucket where Textract results are saved (can be same as SOURCE_BUCKET)
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', SOURCE_BUCKET)

# Prefix for output files (e.g., 'processed/', 'results/', or empty string)
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX', 'processed/')

# ============================================================================
# AWS Configuration
# ============================================================================
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# ============================================================================
# DynamoDB Configuration
# ============================================================================
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'textract-jobs')

# ============================================================================
# Textract Configuration
# ============================================================================
# Features to extract from documents
FEATURE_TYPES = ['FORMS', 'TABLES']

# ============================================================================
# Helper Functions
# ============================================================================

def get_output_key(batch_prefix, filename):
    """
    Generate S3 key for output file.

    Args:
        batch_prefix: Batch folder prefix (e.g., "batch-1/")
        filename: Output filename (e.g., "document.json")

    Returns:
        Full S3 key (e.g., "processed/batch-1/document.json")

    Examples:
        >>> get_output_key("batch-1/", "doc.json")
        'processed/batch-1/doc.json'

        >>> # With empty OUTPUT_PREFIX
        >>> OUTPUT_PREFIX = ""
        >>> get_output_key("batch-1/", "doc.json")
        'batch-1/doc.json'
    """
    if OUTPUT_PREFIX:
        # Remove trailing slash from prefix if present, then add it back
        prefix = OUTPUT_PREFIX.rstrip('/') + '/'
        return f"{prefix}{batch_prefix}{filename}"
    else:
        # No prefix, just batch and filename
        return f"{batch_prefix}{filename}"


def get_s3_uri(bucket, key):
    """
    Generate S3 URI from bucket and key.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        S3 URI (e.g., "s3://bucket/key")
    """
    return f"s3://{bucket}/{key}"
