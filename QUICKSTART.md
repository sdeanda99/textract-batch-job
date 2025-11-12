# Covest Compliance - Quick Start Guide

This project provides automated scripts to process and analyze PDF documents using AWS services (S3, Textract, Lambda, DynamoDB). All configuration is managed through `.env` files for easy setup and reuse.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Setup](#aws-setup)
3. [Project Overview](#project-overview)
4. [Getting Started](#getting-started)
5. [Configuration](#configuration)
6. [What You Can Do](#what-you-can-do)

---

## Prerequisites

### Required Software

- **AWS CLI v2** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Python 3.12+** - [Download Python](https://www.python.org/downloads/)
- **Bash shell** - macOS/Linux (built-in), Windows (use Git Bash or WSL)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **Text editor** - VS Code, nano, vim, etc.

### AWS Account Requirements

You'll need an AWS account with appropriate permissions. See [AWS Permissions](#aws-permissions) below.

---

## AWS Setup

### Step 1: Install AWS CLI

**macOS:**
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows:**
Download and run the AWS CLI MSI installer from [AWS CLI for Windows](https://awscli.amazonaws.com/AWSCLIV2.msi)

**Verify installation:**
```bash
aws --version
# Should show: aws-cli/2.x.x ...
```

---

### Step 2: Configure AWS Credentials

You need to configure AWS CLI with your credentials. Choose ONE of the following methods:

#### **Option A: Using AWS Access Keys (Recommended for Getting Started)**

1. **Get your AWS Access Keys:**
   - Log into AWS Console
   - Go to **IAM** → **Users** → Click your username
   - Go to **Security credentials** tab
   - Click **Create access key**
   - Choose **"Command Line Interface (CLI)"**
   - Download or copy your:
     - Access Key ID
     - Secret Access Key

2. **Configure AWS CLI:**
   ```bash
   aws configure
   ```

3. **Enter your credentials when prompted:**
   ```
   AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
   AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   Default region name [None]: us-east-1
   Default output format [None]: json
   ```

4. **Verify your credentials:**
   ```bash
   aws sts get-caller-identity
   ```

   **Success looks like:**
   ```json
   {
       "UserId": "AIDAI...",
       "Account": "123456789012",
       "Arn": "arn:aws:iam::123456789012:user/your-username"
   }
   ```

---

#### **Option B: Using AWS SSO (If your organization uses SSO)**

1. **Get SSO details from your AWS administrator:**
   - SSO start URL (e.g., `https://my-company.awsapps.com/start`)
   - SSO region (e.g., `us-east-1`)
   - Account ID
   - Role name

2. **Configure SSO:**
   ```bash
   aws configure sso
   ```

3. **Follow the prompts:**
   ```
   SSO start URL [None]: https://my-company.awsapps.com/start
   SSO region [None]: us-east-1
   SSO account ID [None]: 123456789012
   SSO role name [None]: PowerUserAccess
   CLI default client Region [None]: us-east-1
   CLI default output format [None]: json
   CLI profile name [None]: default
   ```

4. **Login to AWS SSO:**
   ```bash
   aws sso login --profile default
   ```

5. **Verify your credentials:**
   ```bash
   aws sts get-caller-identity --profile default
   ```

---

#### **Option C: Using Named Profiles (If you have multiple AWS accounts)**

1. **Configure a named profile:**
   ```bash
   aws configure --profile my-project
   ```

2. **Update `.env` files to use your profile:**
   ```bash
   # In your .env file
   AWS_PROFILE=my-project
   ```

3. **All scripts will automatically use this profile**

---

### Step 3: Test AWS Access

Run these commands to verify you have proper access:

```bash
# Test S3 access
aws s3 ls

# Test IAM access
aws iam get-user

# Test Lambda access
aws lambda list-functions

# Test DynamoDB access
aws dynamodb list-tables
```

**If any command fails with "Access Denied"**, you need additional permissions (see below).

---

## AWS Permissions

Your AWS IAM user/role needs these permissions:

### **Minimum Required Permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "lambda:*",
        "dynamodb:*",
        "textract:*",
        "sns:*",
        "sqs:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:GetRole",
        "iam:PassRole",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### **Recommended: Use AWS Managed Policies**

Ask your AWS administrator to attach these policies to your IAM user:

- `PowerUserAccess` (easiest - has most permissions needed)
- OR individually:
  - `AmazonS3FullAccess`
  - `AWSLambda_FullAccess`
  - `AmazonDynamoDBFullAccess`
  - `AmazonTextractFullAccess`
  - `AmazonSNSFullAccess`
  - `AmazonSQSFullAccess`
  - `IAMFullAccess`

### **Cost Warning**

AWS services used in this project incur costs:
- **S3 Storage**: ~$0.023 per GB/month
- **Lambda**: First 1M requests free, then $0.20 per 1M
- **Textract**: $1.50 per 1,000 pages (forms + tables)
- **DynamoDB**: On-demand pricing (pay per request)
- **SNS/SQS**: First 1M requests free monthly

**Estimated cost for processing 4,000 PDFs (avg 5 pages each):**
- Textract: ~$30
- Other services: ~$5
- **Total: ~$35**

---

## Project Overview

This project has two main workflows:

### **1. S3 PDF Organization** (`functions/lambda/s3_folder_org/`)

**Purpose:** Organize large batches of PDFs into manageable groups

**What it does:**
- Takes thousands of PDFs in an S3 bucket
- Organizes them into batch folders (e.g., `batch-1/`, `batch-2/`)
- Optionally creates separate S3 buckets for each batch

**When to use:** Before processing PDFs with Textract

📖 **[Read the full guide →](functions/lambda/s3_folder_org/README.md)**

---

### **2. Textract PDF Processing** (`functions/lambda/textract_processor/`)

**Purpose:** Extract text, forms, and tables from PDFs using AWS Textract

**What it does:**
- Processes PDFs using AWS Textract (asynchronous batch processing)
- Extracts text, key-value pairs, and tables
- Saves structured JSON results to S3
- Tracks processing status in DynamoDB

**When to use:** After organizing PDFs into batches

📖 **[Read the full guide →](functions/lambda/textract_processor/README.md)**

---

## Getting Started

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd covest-compliance
```

---

### Step 2: Choose Your Workflow

#### **Workflow 1: Organize PDFs** → Go to [`s3_folder_org`](functions/lambda/s3_folder_org/)

```bash
cd functions/lambda/s3_folder_org
cp .env.example .env
# Edit .env with your bucket name and AWS profile
nano .env
```

**Then run:**
```bash
cd scripts
./organize_pdfs.sh
```

---

#### **Workflow 2: Process PDFs with Textract** → Go to [`textract_processor`](functions/lambda/textract_processor/)

```bash
cd functions/lambda/textract_processor
cp .env.example .env
# Edit .env with your configuration
nano .env
```

**Then run the deployment sequence:**
```bash
cd scripts
./01_create_infrastructure.sh
./02_create_iam_roles.sh
./03_deploy_lambdas.sh
./04_configure_triggers.sh
./05_process_batches.sh 1  # Test with batch 1 first
```

---

## Configuration

All scripts use `.env` files for configuration. This approach:

✅ **No hardcoded values** - Everything configurable
✅ **Git-safe** - `.env` is ignored, `.env.example` is committed
✅ **Reusable** - Same scripts work across different AWS accounts
✅ **Flexible** - Override any setting via environment variables

### **Configuration Files:**

```
project-root/
├── functions/lambda/s3_folder_org/
│   ├── .env.example          ← Copy to .env
│   └── config.py             ← Reads from .env
│
├── functions/lambda/textract_processor/
│   ├── .env.example          ← Copy to .env
│   └── config.py             ← Reads from .env
│
└── scripts/
    └── aws_login.sh          ← AWS SSO login helper (optional)
```

### **Common Configuration Settings:**

| Setting | Description | Default |
|---------|-------------|---------|
| `AWS_PROFILE` | AWS CLI profile name | `default` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `SOURCE_BUCKET` | S3 bucket with PDFs | *(required)* |
| `OUTPUT_BUCKET` | S3 bucket for results | Same as SOURCE |

**Full configuration options:** See `.env.example` in each project folder

---

## What You Can Do

### **Organize PDFs in S3:**
```bash
cd functions/lambda/s3_folder_org/scripts
./organize_pdfs.sh
```

### **Process PDFs with Textract:**
```bash
cd functions/lambda/textract_processor/scripts
./05_process_batches.sh 1          # Single batch
./05_process_batches.sh all        # All batches
```

### **Download Textract Results:**
```bash
cd functions/lambda/textract_processor/scripts
./download_results.sh
```

### **Convert Results to Excel:**
```bash
cd functions/lambda/textract_processor/scripts
pip install boto3 openpyxl
python3 convert_to_xlsx.py
```

### **Monitor Processing:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/textract-batch-initiator --follow

# Check DynamoDB status
aws dynamodb scan --table-name textract-jobs

# Check S3 results
aws s3 ls s3://your-bucket/processed/ --recursive
```

---

## Troubleshooting

### **AWS CLI not found**
```bash
# Install AWS CLI (see AWS Setup section above)
aws --version
```

### **Access Denied / Permission Errors**
```bash
# Check your credentials
aws sts get-caller-identity

# Make sure your IAM user has required permissions
# See "AWS Permissions" section above
```

### **Profile not found**
```bash
# List available profiles
aws configure list-profiles

# If using named profile, update your .env:
AWS_PROFILE=your-profile-name
```

### **.env file not found**
```bash
# Copy the example file
cp .env.example .env

# Edit with your settings
nano .env
```

### **Invalid region**
```bash
# Update region in .env
AWS_REGION=us-east-1  # or your preferred region
```

### **Lambda deployment fails**
```bash
# Make sure you have IAM permissions to create Lambda functions
# Wait 10 seconds after creating IAM roles for propagation
# Check CloudWatch logs for detailed errors
```

---

## Project Structure

```
covest-compliance/
├── QUICKSTART.md                          ← You are here
├── README.md                              ← Project overview
├── .env.example                           ← Not used (per-folder config)
├── .gitignore                             ← Excludes .env, legacy/, etc.
│
├── functions/lambda/
│   │
│   ├── s3_folder_org/                     ← PDF Organization
│   │   ├── .env.example                   ← Configuration template
│   │   ├── config.py                      ← Configuration module
│   │   ├── README.md                      ← Full documentation
│   │   ├── CONFIGURATION_GUIDE.md         ← Config details
│   │   ├── lambda_pdf_organizer.py        ← Lambda function
│   │   ├── lambda_bucket_creator.py       ← Lambda function
│   │   └── scripts/
│   │       ├── organize_pdfs.sh           ← Organize PDFs locally
│   │       ├── deploy_and_run.sh          ← Deploy bucket creator
│   │       └── cleanup_duplicates.sh      ← Cleanup utility
│   │
│   └── textract_processor/                ← Textract Processing
│       ├── .env.example                   ← Configuration template
│       ├── config.py                      ← Configuration module
│       ├── README.md                      ← Full documentation
│       ├── lambda_batch_initiator.py      ← Start Textract jobs
│       ├── lambda_result_processor.py     ← Process results
│       └── scripts/
│           ├── 01_create_infrastructure.sh
│           ├── 02_create_iam_roles.sh
│           ├── 03_deploy_lambdas.sh
│           ├── 04_configure_triggers.sh
│           ├── 05_process_batches.sh
│           ├── download_results.sh
│           └── convert_to_xlsx.py
│
└── scripts/
    ├── aws_login.sh                       ← AWS SSO login helper
    └── legacy/                            ← Old scripts (gitignored)
```

---

## Next Steps

1. ✅ **Configure AWS CLI** (see [AWS Setup](#aws-setup))
2. ✅ **Verify permissions** (see [AWS Permissions](#aws-permissions))
3. ✅ **Choose your workflow:**
   - 📁 [Organize PDFs](functions/lambda/s3_folder_org/README.md)
   - 🔍 [Process with Textract](functions/lambda/textract_processor/README.md)
4. ✅ **Copy `.env.example` to `.env`** in your chosen folder
5. ✅ **Edit `.env`** with your AWS settings
6. ✅ **Run the scripts!**

---

## Getting Help

### **Documentation:**
- [S3 PDF Organization Guide](functions/lambda/s3_folder_org/README.md)
- [Textract Processing Guide](functions/lambda/textract_processor/README.md)
- [Configuration Guide](functions/lambda/s3_folder_org/CONFIGURATION_GUIDE.md)

### **Common Issues:**
- Check CloudWatch Logs for Lambda errors
- Verify IAM permissions match requirements
- Ensure `.env` file is configured correctly
- Wait 10 seconds after creating IAM roles

### **AWS Documentation:**
- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
- [AWS Textract](https://docs.aws.amazon.com/textract/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon S3](https://docs.aws.amazon.com/s3/)

---

## Contributing

When contributing or sharing this project:

1. **Never commit `.env` files** - They're in `.gitignore`
2. **Update `.env.example`** - If you add new configuration options
3. **Test with minimal permissions** - Ensure IAM requirements are documented
4. **Update READMEs** - Keep documentation in sync with code changes

---

## License

*(Add your license information here)*

---

## Support

For questions, issues, or suggestions:
- Check the README files in each project folder
- Review CloudWatch logs for detailed error messages
- Verify AWS permissions and configuration
- Check that `.env` values match your AWS account

---

**Happy Processing! 🚀**
