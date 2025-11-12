# Configuration Guide

This guide explains how configuration works in the S3 PDF Organization scripts.

## Quick Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```bash
   # Required - change these!
   SOURCE_BUCKET=your-bucket-name-here
   AWS_PROFILE=your-aws-profile-name

   # Optional - defaults provided
   AWS_REGION=us-east-1
   BATCH_SIZE=150
   LAMBDA_FUNCTION_NAME=s3-bucket-creator
   LAMBDA_ROLE_NAME=lambda-s3-bucket-creator-role
   LAMBDA_TIMEOUT=900
   LAMBDA_MEMORY=1024
   ```

3. Run any script - they'll automatically use your `.env` configuration!

## How Configuration Works

### Bash Scripts
All bash scripts (`.sh` files) automatically:
1. Look for `.env` file in the parent directory
2. Load and export all variables from `.env`
3. Provide helpful error if `.env` is missing
4. Use environment variables with fallback defaults

**Example from `organize_pdfs.sh`:**
```bash
# Load .env file
source "$SCRIPT_DIR/.env"

# Use environment variables
BUCKET="${SOURCE_BUCKET}"
BATCH_SIZE="${BATCH_SIZE:-150}"  # Defaults to 150 if not set
```

### Python Scripts (Lambda Functions)
Python Lambda functions use the `config.py` module:
1. `config.py` reads from `os.environ` (environment variables)
2. Provides sensible defaults if variables aren't set
3. Lambda functions import and use values from `config.py`
4. Event payload can still override defaults

**Example from `lambda_bucket_creator.py`:**
```python
import config

def lambda_handler(event, context):
    # Uses config.py which reads from environment
    source_bucket = event.get('source_bucket', config.SOURCE_BUCKET)
    region = event.get('region', config.AWS_REGION)
```

### Priority Order
Configuration values are resolved in this order (highest to lowest priority):

1. **Event payload** (for Lambda functions only) - highest priority
2. **Environment variables** (from `.env` or Lambda environment)
3. **Default values** (in `config.py`) - lowest priority

## File Overview

### `.env.example`
Template file showing all available configuration options. This file IS committed to git so others can see what to configure.

### `.env`
Your actual configuration file with real values. This file is git-ignored and NEVER committed to prevent exposing sensitive information like bucket names and AWS profiles.

### `config.py`
Python module that reads configuration from environment variables and provides defaults. This is imported by both Lambda functions.

### `.gitignore`
Updated to exclude `.env` files from version control.

## Deploying Lambda Functions

When you run `deploy_and_run.sh`:
1. Script reads your `.env` file
2. Packages `lambda_bucket_creator.py` AND `config.py` into zip
3. Creates/updates Lambda function
4. Sets Lambda environment variables from your `.env`:
   - `SOURCE_BUCKET`
   - `AWS_REGION`
   - `BATCH_SIZE`
5. Lambda function uses these environment variables via `config.py`

## Benefits of This Approach

1. **No hardcoded values** - All configuration in one place
2. **Git-safe** - `.env` is ignored, sensitive data stays private
3. **Reusable** - Same scripts work across different AWS accounts
4. **Flexible** - Can override via event payloads
5. **Simple** - No external dependencies (no python-dotenv needed)
6. **Documented** - `.env.example` shows what's configurable

## Troubleshooting

### "Error: .env file not found"
**Solution:** Copy `.env.example` to `.env` and configure it:
```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

### Lambda function uses wrong bucket
**Solution:** Check Lambda environment variables match your `.env`:
```bash
aws lambda get-function-configuration \
  --function-name s3-bucket-creator \
  --profile your-profile \
  --query 'Environment.Variables'
```

Then re-run `deploy_and_run.sh` to update environment variables.

### Script can't find .env file
**Solution:** Make sure you're running scripts from the correct directory, or that `.env` is in the `s3_folder_org` directory (not in `scripts` subdirectory).

## Security Best Practices

1. **Never commit `.env`** - It's in `.gitignore` for a reason
2. **Use IAM roles in production** - Avoid embedding credentials
3. **Rotate AWS credentials regularly** - Update AWS profile credentials
4. **Limit S3 bucket permissions** - Use least-privilege IAM policies
5. **Review `.env.example`** - Make sure no sensitive data is in the example file

## For GitHub Users

When uploading this project to GitHub:
- `.env.example` will be included (template)
- `.env` will NOT be included (your actual config)
- Other users copy `.env.example` to `.env` and configure for their AWS account
- Everyone can use the same scripts with different configurations!
