# AWS Textract Batch Processor

This project processes large batches of PDF documents using AWS Textract to extract text, forms (key-value pairs), and tables. All configuration is managed through environment variables for easy reuse across different AWS accounts and projects.

## Quick Start

1. **Copy the environment template:**
   ```bash
   cd functions/lambda/textract_processor
   cp .env.example .env
   ```

2. **Edit `.env` with your AWS configuration:**
   ```bash
   # Edit these values for your AWS account
   SOURCE_BUCKET=your-bucket-name-here
   OUTPUT_BUCKET=your-results-bucket-here
   AWS_PROFILE=your-aws-profile
   AWS_REGION=us-east-1
   ```

3. **Run the deployment scripts** (see Deployment Sequence below)

## Architecture Overview

```
S3 Bucket (SOURCE_BUCKET)
├── batch-1/ (PDFs)
├── batch-2/ (PDFs)
└── batch-N/ (PDFs)
    ↓
Lambda 1: textract-batch-initiator
├── Lists PDFs in batch folder
├── Calls Textract StartDocumentAnalysis
└── Stores JobId in DynamoDB
    ↓
AWS Textract (Asynchronous Processing)
├── Extracts text, forms, and tables
└── Sends completion notification to SNS
    ↓
SNS Topic → SQS Queue
    ↓
Lambda 2: textract-result-processor
├── Retrieves results from Textract
├── Parses text, key-value pairs, and tables
└── Saves JSON to S3: OUTPUT_BUCKET/OUTPUT_PREFIX/batch-X/filename.json
```

## Configuration

All configuration is managed through environment variables defined in a `.env` file. This makes it easy to reuse these scripts across different projects and AWS accounts.

### Environment Variables

Create a `.env` file in the `textract_processor` directory with these variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SOURCE_BUCKET` | S3 bucket containing PDFs to process | *(required)* |
| `OUTPUT_BUCKET` | S3 bucket for Textract results (can be same as SOURCE_BUCKET) | Same as SOURCE_BUCKET |
| `OUTPUT_PREFIX` | Prefix for results (e.g., "processed/", "results/") | `processed/` |
| `AWS_REGION` | AWS region for resources | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile name | `default` |
| `BATCH_PREFIX_PATTERN` | Pattern for batch folders | `batch-` |
| `TOTAL_BATCHES` | Total number of batch folders to process | `29` |
| `OUTPUT_RESULTS_DIR` | Local directory for downloaded results | `../textract_results` |
| `DYNAMODB_TABLE_NAME` | DynamoDB table name for job tracking | `textract-jobs` |
| `SNS_TOPIC_NAME` | SNS topic name for notifications | `textract-completion-topic` |
| `SQS_QUEUE_NAME` | SQS queue name for results | `textract-results-queue` |
| `TEXTRACT_ROLE_NAME` | IAM role name for Textract | `textract-sns-role` |
| `LAMBDA_INITIATOR_ROLE_NAME` | IAM role for initiator Lambda | `lambda-textract-initiator-role` |
| `LAMBDA_PROCESSOR_ROLE_NAME` | IAM role for processor Lambda | `lambda-textract-processor-role` |
| `LAMBDA_INITIATOR_NAME` | Lambda function name for initiator | `textract-batch-initiator` |
| `LAMBDA_PROCESSOR_NAME` | Lambda function name for processor | `textract-result-processor` |
| `LAMBDA_INITIATOR_TIMEOUT` | Timeout in seconds for initiator | `300` |
| `LAMBDA_INITIATOR_MEMORY` | Memory in MB for initiator | `512` |
| `LAMBDA_PROCESSOR_TIMEOUT` | Timeout in seconds for processor | `300` |
| `LAMBDA_PROCESSOR_MEMORY` | Memory in MB for processor | `1024` |
| `LAMBDA_RUNTIME` | Python runtime version | `python3.12` |

**Note:** A `.env.example` template is provided. Copy it to `.env` and update with your values.

## Components

### Lambda Functions

Both Lambda functions use the `config.py` module to read configuration from environment variables set during deployment.

#### 1. **textract-batch-initiator**
**Purpose:** Initiates Textract jobs for all PDFs in a batch folder.

**What it does:**
- Lists all PDF files in the specified batch folder
- Starts asynchronous Textract document analysis for each PDF
- Stores job metadata in DynamoDB for tracking
- Configurable via environment variables

**Configuration:**
- Reads from `config.py` which uses Lambda environment variables
- Can be overridden via event payload

---

#### 2. **textract-result-processor**
**Purpose:** Retrieves and saves Textract results when processing completes.

**What it does:**
- Triggered automatically by SQS messages (from SNS)
- Retrieves completed Textract results
- Extracts and structures text, forms, and tables
- Saves JSON results to configured S3 bucket/prefix
- Updates DynamoDB job status

**Configuration:**
- Reads from `config.py` which uses Lambda environment variables
- Uses `OUTPUT_BUCKET` and `OUTPUT_PREFIX` for saving results

---

### Infrastructure

All resource names are configurable via `.env`:

- **DynamoDB Table**: Tracks job status and metadata
- **SNS Topic**: Receives Textract completion notifications
- **SQS Queue**: Buffers completion messages for Lambda processing
- **S3 Output**: Configurable bucket and prefix for results

### IAM Roles

Three IAM roles are created automatically:

1. **Textract SNS Role**: Allows Textract to publish completion notifications to SNS
2. **Lambda Initiator Role**: Allows Lambda to start Textract jobs, read from S3, and write to DynamoDB
3. **Lambda Processor Role**: Allows Lambda to retrieve Textract results, read/write S3, access DynamoDB, and consume SQS messages

## Deployment Sequence

### Prerequisites

- **AWS CLI** installed and configured
- **AWS Profile** configured with credentials
- **IAM Permissions:**
  - S3: Read, Write, List
  - Lambda: Create Function, Invoke, Update
  - IAM: Create Role, Attach Policy
  - DynamoDB: Create Table, Read, Write
  - SNS: Create Topic, Publish, Subscribe
  - SQS: Create Queue, Send/Receive Messages
  - Textract: StartDocumentAnalysis, GetDocumentAnalysis
- **Python 3.12+** (for Lambda functions)
- **Bash shell** (for running scripts)

---

### Step 0: Setup Configuration

**First time only:** Create and configure your `.env` file

```bash
cd functions/lambda/textract_processor
cp .env.example .env
# Edit .env with your AWS account details
nano .env  # or use your preferred editor
```

**Required changes:**
- Set `SOURCE_BUCKET` to your bucket containing PDFs
- Set `OUTPUT_BUCKET` to where you want results saved
- Set `AWS_PROFILE` to your AWS CLI profile name
- Adjust `TOTAL_BATCHES` if different from 29

---

### Step 1: Create Infrastructure

Navigate to scripts directory and create AWS infrastructure:

```bash
cd functions/lambda/textract_processor/scripts
./01_create_infrastructure.sh
```

**This creates:**
- DynamoDB table for job tracking
- SNS topic for Textract notifications
- SQS queue to buffer messages
- Subscriptions between SNS and SQS
- Saves configuration to `infrastructure_config.sh`

**Time:** ~2 minutes

---

### Step 2: Create IAM Roles

Create required IAM roles and policies:

```bash
./02_create_iam_roles.sh
```

**This creates:**
- Textract SNS role (allows Textract to publish notifications)
- Lambda initiator role (allows Lambda to start Textract jobs)
- Lambda processor role (allows Lambda to retrieve results)
- All policies are automatically configured based on your `.env`

**Time:** ~1 minute (includes 10-second propagation wait)

---

### Step 3: Deploy Lambda Functions

Package and deploy both Lambda functions:

```bash
./03_deploy_lambdas.sh
```

**This does:**
- Packages each Lambda function with `config.py` into ZIP files
- Creates or updates Lambda functions in AWS
- Sets Lambda environment variables from your `.env`
- Configures runtime, timeout, and memory settings
- Waits for functions to be active

**Time:** ~2 minutes

**Note:** Lambda functions will use configuration from environment variables, no code changes needed!

---

### Step 4: Configure Triggers

Set up SQS event source for Lambda:

```bash
./04_configure_triggers.sh
```

**This configures:**
- SQS queue as event source for processor Lambda
- Batch size of 10 messages
- Enables automatic triggering when results arrive

**Time:** ~30 seconds

---

### Step 5: Process Batches

Start processing your PDF batches:

```bash
# Test with a single batch first
./05_process_batches.sh 1

# Process all batches (will prompt for confirmation)
./05_process_batches.sh all

# Or process a specific batch
./05_process_batches.sh 5
```

**What happens:**
1. Lambda initiator starts Textract jobs for all PDFs in batch
2. Textract processes PDFs asynchronously (5-30 seconds each)
3. Textract sends completion notifications to SNS
4. SNS forwards to SQS queue
5. Lambda processor automatically retrieves and saves results
6. Results saved to: `s3://OUTPUT_BUCKET/OUTPUT_PREFIX/batch-N/filename.json`

**Time:** Varies based on number of PDFs and pages

---

### Step 6: Download Results (Optional)

Download processed results to your local machine:

```bash
./download_results.sh
```

**This downloads:**
- All JSON results from `OUTPUT_BUCKET/OUTPUT_PREFIX`
- Saves to local directory specified in `OUTPUT_RESULTS_DIR`
- Ready for conversion to Excel or other formats

---

### Step 7: Convert to Excel (Optional)

Convert JSON results to Excel format:

```bash
# Install dependencies if needed
pip install boto3 openpyxl

# Convert results
python3 convert_to_xlsx.py
```

**Output:** `textract_results.xlsx` with all extracted data

---

## Processing Flow

### Input
- **Source:** `s3://SOURCE_BUCKET/batch-N/*.pdf`
- **Format:** PDF documents organized in batch folders
- **Configurable:** Batch prefix pattern and total batches via `.env`

### Output
- **Location:** `s3://OUTPUT_BUCKET/OUTPUT_PREFIX/batch-N/filename.json`
- **Format:** JSON with structured data
- **Configurable:** Bucket and prefix via `.env`

### Output JSON Structure

```json
{
  "raw_text": [
    {
      "text": "Line of text from document",
      "confidence": 99.5
    }
  ],
  "key_value_pairs": [
    {
      "key": "Name",
      "value": "John Doe",
      "confidence": 98.2
    }
  ],
  "tables": [
    {
      "rows": [
        ["Header 1", "Header 2"],
        ["Value 1", "Value 2"]
      ],
      "confidence": 97.8
    }
  ],
  "metadata": {
    "source_file": "batch-1/document.pdf",
    "bucket": "your-source-bucket",
    "batch": "batch-1/",
    "job_id": "abc123...",
    "processed_time": "2025-11-12T14:30:00Z",
    "total_blocks": 1234
  }
}
```

## Monitoring Progress

All monitoring commands automatically use your `.env` configuration:

### Check Lambda Logs

```bash
# Initiator Lambda (shows jobs being started)
aws logs tail /aws/lambda/$LAMBDA_INITIATOR_NAME --follow --profile $AWS_PROFILE

# Processor Lambda (shows results being saved)
aws logs tail /aws/lambda/$LAMBDA_PROCESSOR_NAME --follow --profile $AWS_PROFILE
```

### Check Job Status in DynamoDB

```bash
aws dynamodb scan \
  --table-name $DYNAMODB_TABLE_NAME \
  --profile $AWS_PROFILE \
  --region $AWS_REGION
```

### Check SQS Queue Depth

```bash
# Load infrastructure config
source scripts/infrastructure_config.sh

aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages \
  --profile $AWS_PROFILE \
  --region $AWS_REGION
```

### Check Processed Files in S3

```bash
aws s3 ls s3://$OUTPUT_BUCKET/$OUTPUT_PREFIX \
  --recursive \
  --profile $AWS_PROFILE
```

### Monitor Processing Progress

Track how many jobs have completed:

```bash
# Count completed jobs
aws dynamodb scan \
  --table-name $DYNAMODB_TABLE_NAME \
  --filter-expression "#status = :status" \
  --expression-attribute-names '{"#status": "Status"}' \
  --expression-attribute-values '{":status": {"S": "COMPLETED"}}' \
  --select COUNT \
  --profile $AWS_PROFILE
```

## Utility Scripts

### `process_remaining_batches.sh`

Process multiple batches sequentially with delays:

```bash
# Start from batch 2 (assumes batch 1 already processed)
./process_remaining_batches.sh

# Start from a specific batch
./process_remaining_batches.sh 5  # Start from batch 5
```

**What it does:**
- Processes batches from START_BATCH to TOTAL_BATCHES
- Adds 60-second delay between batches to avoid throttling
- Dynamically reads TOTAL_BATCHES from `.env`

---

### `recover_failed_notifications.py`

Recover from missed SNS notifications:

```bash
python3 recover_failed_notifications.py
```

**What it does:**
- Scans DynamoDB for jobs stuck in IN_PROGRESS state
- Checks Textract status for these jobs
- Manually triggers result processing if completed
- Useful if SNS notifications were missed

---

## Important Notes

### Configuration
- **`.env` file is git-ignored** - Your configuration won't be committed to version control
- **All scripts read from `.env`** - No need to manually edit hardcoded values
- **Lambda functions use environment variables** - Set during deployment from `.env`
- **Consistent configuration** - Same `.env` drives bash scripts, Python scripts, and Lambda functions

### AWS Limits
- **150 documents per batch** - Recommended to avoid throttling
- **Job results stored for 7 days** - Retrieve within this window
- **Processing time**: Multi-page documents take 5-30 seconds each
- **Concurrent job limits**: AWS may throttle if too many concurrent requests
- **Pagination required**: Large documents handled automatically

### Best Practices
1. **Test with single batch first** - Use `./05_process_batches.sh 1` before processing all
2. **Monitor logs** - Watch Lambda logs during first batch
3. **Check costs** - Review AWS billing for Textract usage
4. **Use delays** - Scripts include 60-second delays between batches
5. **Backup results** - Download results locally after processing

## Cost Considerations

- **Textract**: $1.50 per 1,000 pages for forms + tables extraction
- **Lambda**: First 1M requests/month free, then $0.20 per 1M requests
- **DynamoDB**: On-demand pricing (pay per request)
- **S3**: Storage + API requests
- **SQS**: First 1M requests/month free
- **SNS**: First 1M publishes/month free

**Example:** 4,331 PDFs with avg 5 pages each:
- ~21,655 pages × $1.50/1000 = ~$32.50 for Textract
- Lambda, DynamoDB, S3, SQS, SNS costs typically < $5 for this volume

## Troubleshooting

### Error: .env file not found
**Solution:** Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
nano .env
```

### Lambda timeout errors
**Solution:** Increase timeout in `.env`:
```bash
LAMBDA_INITIATOR_TIMEOUT=600  # Increase to 10 minutes
LAMBDA_PROCESSOR_TIMEOUT=600
```
Then redeploy: `./03_deploy_lambdas.sh`

### Textract job failed
**Causes:**
- PDF is encrypted or corrupted
- IAM permissions missing
- PDF format not supported

**Solution:**
- Check CloudWatch logs for error details
- Verify PDF can be opened normally
- Check IAM role permissions

### Results not appearing in S3
**Checks:**
1. Verify Lambda processor logs show successful processing
2. Check SQS trigger is enabled: `aws lambda list-event-source-mappings`
3. Check DynamoDB for job status
4. Verify OUTPUT_BUCKET and OUTPUT_PREFIX settings

### Permission errors
**Solution:**
- Wait 10 seconds after creating IAM roles
- Check trust relationships in IAM console
- Verify your AWS_PROFILE has sufficient permissions
- Re-run `./02_create_iam_roles.sh` to update policies

### Wrong bucket or configuration used
**Solution:**
- Verify `.env` file values
- Check Lambda environment variables in AWS Console
- Redeploy Lambda functions: `./03_deploy_lambdas.sh`

## Files Included

- **`.env.example`** - Template for environment configuration (copy to `.env`)
- **`config.py`** - Python configuration module that reads environment variables
- **`lambda_batch_initiator.py`** - Lambda function to start Textract jobs
- **`lambda_result_processor.py`** - Lambda function to retrieve and save results
- **`scripts/01_create_infrastructure.sh`** - Creates DynamoDB, SNS, SQS
- **`scripts/02_create_iam_roles.sh`** - Creates IAM roles and policies
- **`scripts/03_deploy_lambdas.sh`** - Deploys Lambda functions with config
- **`scripts/04_configure_triggers.sh`** - Sets up SQS event source
- **`scripts/05_process_batches.sh`** - Starts batch processing
- **`scripts/download_results.sh`** - Downloads results from S3
- **`scripts/process_remaining_batches.sh`** - Process multiple batches sequentially
- **`scripts/convert_to_xlsx.py`** - Converts JSON results to Excel
- **`scripts/recover_failed_notifications.py`** - Recovers from missed notifications
- **`README.md`** - This documentation file

## Cleanup

To remove all AWS resources:

```bash
# Load configuration
source scripts/infrastructure_config.sh

# Delete Lambda functions
aws lambda delete-function --function-name $LAMBDA_INITIATOR_NAME --profile $AWS_PROFILE
aws lambda delete-function --function-name $LAMBDA_PROCESSOR_NAME --profile $AWS_PROFILE

# Delete event source mapping
aws lambda delete-event-source-mapping --uuid $EVENT_SOURCE_MAPPING_UUID --profile $AWS_PROFILE

# Delete SQS queue
aws sqs delete-queue --queue-url $SQS_QUEUE_URL --profile $AWS_PROFILE

# Delete SNS topic
aws sns delete-topic --topic-arn $SNS_TOPIC_ARN --profile $AWS_PROFILE

# Delete DynamoDB table
aws dynamodb delete-table --table-name $DYNAMODB_TABLE_NAME --profile $AWS_PROFILE

# Delete IAM roles and policies
aws iam delete-role-policy --role-name $TEXTRACT_ROLE_NAME --policy-name TextractSNSPublishPolicy --profile $AWS_PROFILE
aws iam delete-role --role-name $TEXTRACT_ROLE_NAME --profile $AWS_PROFILE

aws iam detach-role-policy --role-name $LAMBDA_INITIATOR_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --profile $AWS_PROFILE
aws iam delete-role-policy --role-name $LAMBDA_INITIATOR_ROLE_NAME --policy-name LambdaInitiatorPolicy --profile $AWS_PROFILE
aws iam delete-role --role-name $LAMBDA_INITIATOR_ROLE_NAME --profile $AWS_PROFILE

aws iam detach-role-policy --role-name $LAMBDA_PROCESSOR_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --profile $AWS_PROFILE
aws iam delete-role-policy --role-name $LAMBDA_PROCESSOR_ROLE_NAME --policy-name LambdaProcessorPolicy --profile $AWS_PROFILE
aws iam delete-role --role-name $LAMBDA_PROCESSOR_ROLE_NAME --profile $AWS_PROFILE

# Optionally delete processed results from S3
aws s3 rm s3://$OUTPUT_BUCKET/$OUTPUT_PREFIX --recursive --profile $AWS_PROFILE
```

## For GitHub Users

When uploading this project to GitHub:
- `.env.example` will be included (template)
- `.env` will NOT be included (your actual config is in `.gitignore`)
- Other users copy `.env.example` to `.env` and configure for their AWS account
- Everyone can use the same scripts with different configurations!

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review AWS Textract documentation: https://docs.aws.amazon.com/textract/
3. Verify IAM permissions and resource limits
4. Check `.env` configuration values
5. Ensure Lambda environment variables match your `.env`

## Next Steps

After processing PDFs with Textract, you can:
1. Download results with `download_results.sh`
2. Convert to Excel with `convert_to_xlsx.py`
3. Import to Google Sheets, n8n, or other automation tools
4. Parse JSON for specific key-value pairs or tables
5. Build custom workflows based on extracted data
