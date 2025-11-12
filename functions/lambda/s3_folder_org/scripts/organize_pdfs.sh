#!/bin/bash

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please copy .env.example to .env and configure your settings:"
    echo "  cp $SCRIPT_DIR/.env.example $ENV_FILE"
    exit 1
fi

# Export variables from .env
set -a
source "$ENV_FILE"
set +a

# Configuration from environment variables
BUCKET="${SOURCE_BUCKET}"
BATCH_SIZE="${BATCH_SIZE:-150}"
AWS_PROFILE="${AWS_PROFILE:-default}"

echo "Starting PDF organization into batches..."
echo "Bucket: $BUCKET"
echo "Batch size: $BATCH_SIZE files per batch"
echo ""

# Get list of all PDF files
echo "Fetching list of PDF files..."
aws s3 ls s3://$BUCKET/ --recursive --profile $AWS_PROFILE | grep '\.pdf$' | awk '{for(i=4;i<=NF;i++) printf "%s%s", $i, (i<NF ? " " : "\n")}' > /tmp/pdf_list.txt

# Count total files
TOTAL_FILES=$(wc -l < /tmp/pdf_list.txt)
echo "Total PDF files found: $TOTAL_FILES"

# Calculate number of batches
TOTAL_BATCHES=$(( ($TOTAL_FILES + $BATCH_SIZE - 1) / $BATCH_SIZE ))
echo "Will create $TOTAL_BATCHES batches"
echo ""

# Process files in batches
BATCH_NUM=1
FILE_COUNT=0

while IFS= read -r file; do
    # Calculate current batch number
    BATCH_NUM=$(( ($FILE_COUNT / $BATCH_SIZE) + 1 ))
    BATCH_FOLDER="batch-$BATCH_NUM"

    # Get just the filename (without any existing path)
    FILENAME=$(basename "$file")

    # Copy file to batch folder
    echo "[$FILE_COUNT/$TOTAL_FILES] Copying to $BATCH_FOLDER: $FILENAME"
    aws s3 cp "s3://$BUCKET/$file" "s3://$BUCKET/$BATCH_FOLDER/$FILENAME" --profile $AWS_PROFILE

    FILE_COUNT=$((FILE_COUNT + 1))
done < /tmp/pdf_list.txt

echo ""
echo "✓ Complete! Organized $TOTAL_FILES PDF files into $TOTAL_BATCHES batches."
echo ""
echo "Summary:"
for i in $(seq 1 $TOTAL_BATCHES); do
    COUNT=$(aws s3 ls s3://$BUCKET/batch-$i/ --profile $AWS_PROFILE | wc -l)
    echo "  batch-$i: $COUNT files"
done

# Cleanup
rm /tmp/pdf_list.txt
