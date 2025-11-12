"""
Configuration module for S3 PDF Organization scripts.
Reads configuration from environment variables with sensible defaults.
"""
import os

# S3 Configuration
SOURCE_BUCKET = os.environ.get('SOURCE_BUCKET', 'important-stuff-20251106-0-018ql4')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '150'))

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_PROFILE = os.environ.get('AWS_PROFILE', 'default')

# Lambda Configuration
LAMBDA_FUNCTION_NAME = os.environ.get('LAMBDA_FUNCTION_NAME', 's3-bucket-creator')
LAMBDA_ROLE_NAME = os.environ.get('LAMBDA_ROLE_NAME', 'lambda-s3-bucket-creator-role')
LAMBDA_TIMEOUT = int(os.environ.get('LAMBDA_TIMEOUT', '900'))
LAMBDA_MEMORY = int(os.environ.get('LAMBDA_MEMORY', '1024'))
