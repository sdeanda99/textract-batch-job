# S3 PDF Organization Scripts

This folder contains scripts to organize large batches of PDF files in S3 buckets. The process involves organizing PDFs into batch folders, then optionally creating separate S3 buckets for each batch.

## Quick Start

1. **Copy the environment template:**
   ```bash
   cd functions/lambda/s3_folder_org
   cp .env.example .env
   ```

2. **Edit `.env` with your AWS configuration:**
   ```bash
   # Edit these values for your AWS account
   SOURCE_BUCKET=your-bucket-name-here
   AWS_PROFILE=your-aws-profile
   AWS_REGION=us-east-1
   BATCH_SIZE=150
   ```

3. **Run the scripts** (see Execution Sequence below)

## Overview

The organization process is designed to handle mass PDF uploads by:
1. Grouping PDFs into batches of 150 files each
2. Creating separate S3 buckets for each batch (optional, for Textract processing)
3. Cleaning up any duplicate buckets (if needed)

## Configuration

All configuration is managed through environment variables defined in a `.env` file. This makes it easy to reuse these scripts across different projects and AWS accounts.

### Environment Variables

Create a `.env` file in the `s3_folder_org` directory with these variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SOURCE_BUCKET` | Your S3 bucket name containing PDFs | `important-stuff-20251106-0-018ql4` |
| `BATCH_SIZE` | Number of PDFs per batch | `150` |
| `AWS_REGION` | AWS region for your resources | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile name | `default` |
| `LAMBDA_FUNCTION_NAME` | Name for the Lambda function | `s3-bucket-creator` |
| `LAMBDA_ROLE_NAME` | Name for the Lambda IAM role | `lambda-s3-bucket-creator-role` |
| `LAMBDA_TIMEOUT` | Lambda timeout in seconds | `900` |
| `LAMBDA_MEMORY` | Lambda memory in MB | `1024` |

**Note:** A `.env.example` template is provided. Copy it to `.env` and update with your values.

## Scripts

### Lambda Functions

#### `lambda_pdf_organizer.py`
**Purpose:** AWS Lambda function that organizes all PDFs in a source bucket into batch folders.

**What it does:**
- Scans the source S3 bucket for all PDF files
- Copies PDFs into folders named `batch-1/`, `batch-2/`, etc. (150 files per batch)
- Skips PDFs already in batch folders
- Returns summary of batches created

**When to use:** When you want to use Lambda to organize PDFs (scalable, serverless approach)

**Configuration:**
- Reads from `config.py` which uses environment variables
- Can be overridden via Lambda event payload: `{"bucket_name": "...", "batch_size": 150}`

---

#### `lambda_bucket_creator.py`
**Purpose:** AWS Lambda function that creates individual S3 buckets for each batch folder.

**What it does:**
- Lists all `batch-N` folders in the source bucket
- Creates a new S3 bucket for each batch with naming: `batch-{N}-{timestamp}-{random6chars}`
- Copies all PDFs from each batch folder to its corresponding bucket
- Returns list of created buckets and file counts

**When to use:** After organizing PDFs into batches, when you need separate buckets for parallel Textract processing

**Configuration:**
- Reads from `config.py` which uses environment variables
- Can be overridden via Lambda event payload: `{"source_bucket": "...", "region": "us-east-1"}`

---

### Shell Scripts

#### `scripts/organize_pdfs.sh`
**Purpose:** Local bash script that does the same job as `lambda_pdf_organizer.py` but runs from your machine.

**What it does:**
- Uses AWS CLI to list all PDFs in the bucket
- Copies files into batch folders (`batch-1/`, `batch-2/`, etc.)
- Shows progress as files are copied
- Displays summary of batches created

**When to use:** When you prefer to run organization locally or don't want to use Lambda

**Configuration:**
- Reads configuration from `.env` file automatically
- Requires: `SOURCE_BUCKET`, `BATCH_SIZE`, `AWS_PROFILE`

**Requirements:**
- AWS CLI installed and configured
- AWS profile with S3 read/write permissions

---

#### `scripts/deploy_and_run.sh`
**Purpose:** Deployment script that sets up and executes the bucket creator Lambda function.

**What it does:**
1. Creates IAM role with S3 and Lambda permissions (if doesn't exist)
2. Packages `lambda_bucket_creator.py` and `config.py` into a zip file
3. Creates or updates the Lambda function
4. Invokes the Lambda function to create batch buckets
5. Displays the results

**When to use:** After PDFs are organized into batch folders, to create individual buckets per batch

**Configuration:**
- Reads configuration from `.env` file automatically
- Requires: `SOURCE_BUCKET`, `LAMBDA_FUNCTION_NAME`, `LAMBDA_ROLE_NAME`, `AWS_REGION`, `AWS_PROFILE`, `LAMBDA_TIMEOUT`, `LAMBDA_MEMORY`

**Requirements:**
- AWS CLI installed and configured
- IAM permissions to create roles and Lambda functions

---

#### `scripts/cleanup_duplicates.sh`
**Purpose:** Utility script to remove duplicate batch buckets.

**What it does:**
- Lists all buckets matching pattern `batch-*`
- For each batch number (1-29), keeps only the first bucket found
- Prompts for confirmation before deletion
- Deletes duplicate buckets and their contents

**When to use:** If you accidentally ran the bucket creator multiple times and have duplicate buckets

**Configuration:**
- Reads configuration from `.env` file automatically
- Requires: `AWS_PROFILE`

**Warning:** This script permanently deletes S3 buckets and their contents. Review carefully before confirming.

---

## Recommended Execution Sequence

### Step 0: Setup Configuration
**First time only:** Create and configure your `.env` file
```bash
cd functions/lambda/s3_folder_org
cp .env.example .env
# Edit .env with your AWS account details
```

### Phase 1: Organize PDFs into Batches
Choose ONE method:

**Option A - Using Bash Script (Local execution):**
```bash
cd functions/lambda/s3_folder_org/scripts
./organize_pdfs.sh
```

**Option B - Using Lambda (Serverless):**
1. Deploy `lambda_pdf_organizer.py` as a Lambda function manually
2. Set environment variables in Lambda from your `.env` file
3. Invoke with optional payload override:
```json
{
  "bucket_name": "override-bucket-name",
  "batch_size": 150
}
```

### Phase 2: Create Individual Batch Buckets
Run the deployment script (automatically deploys and invokes the Lambda):
```bash
cd functions/lambda/s3_folder_org/scripts
./deploy_and_run.sh
```

This creates separate S3 buckets for each batch, preparing them for parallel Textract processing.

### Phase 3: Cleanup (Optional)
If you have duplicate buckets:
```bash
cd functions/lambda/s3_folder_org/scripts
./cleanup_duplicates.sh
```

---

## Prerequisites

- **AWS CLI** installed and configured
- **AWS Profile** configured with credentials
- **IAM Permissions:**
  - S3: Read, Write, List, Create Bucket
  - Lambda: Create Function, Invoke (for Lambda approach)
  - IAM: Create Role, Attach Policy (for deploy_and_run.sh)
- **Python 3.12+** (for Lambda functions)

---

## Files Included

- **`.env.example`** - Template for environment configuration (copy to `.env`)
- **`config.py`** - Python configuration module that reads environment variables
- **`lambda_pdf_organizer.py`** - Lambda function for organizing PDFs into batches
- **`lambda_bucket_creator.py`** - Lambda function for creating individual batch buckets
- **`scripts/organize_pdfs.sh`** - Local bash script for organizing PDFs
- **`scripts/deploy_and_run.sh`** - Deployment script for bucket creator Lambda
- **`scripts/cleanup_duplicates.sh`** - Utility to remove duplicate batch buckets
- **`README.md`** - This documentation file

---

## Important Notes

- **`.env` file is git-ignored** - Your configuration won't be committed to version control
- **All scripts read from `.env`** - No need to manually edit hardcoded values anymore
- **Lambda functions use `config.py`** - Which reads from environment variables
- **Event payloads override defaults** - You can override config values when invoking Lambda functions

---

## Next Steps

After organizing PDFs into separate batch buckets, proceed to the `textract-processor` folder to run batch Textract processing on each bucket.
