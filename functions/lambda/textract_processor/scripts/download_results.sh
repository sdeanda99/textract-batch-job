#!/bin/bash

set -e

# Load user configuration from .env
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

# Configuration from .env
OUTPUT_DIR="${OUTPUT_RESULTS_DIR:-../textract_results}"

echo "====================================================================="
echo "Downloading Textract Results from S3"
echo "====================================================================="
echo ""
echo "Source: s3://$OUTPUT_BUCKET/$OUTPUT_PREFIX"
echo "Destination: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Download all processed JSON files
echo "Downloading all JSON results..."
aws s3 sync \
    s3://$OUTPUT_BUCKET/$OUTPUT_PREFIX \
    "$OUTPUT_DIR" \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --exclude "*" \
    --include "*.json"

# Count files
TOTAL_FILES=$(find "$OUTPUT_DIR" -name "*.json" | wc -l | tr -d ' ')

echo ""
echo "====================================================================="
echo "✓ Download Complete!"
echo "====================================================================="
echo ""
echo "Downloaded: $TOTAL_FILES JSON files"
echo "Location: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Install dependencies: pip install boto3 openpyxl"
echo "  2. Run: python3 ./scripts/convert_to_xlsx.py - Convert to Excel format"
echo "  3. Import textract_results.xlsx to Google Sheets or n8n"
echo ""
