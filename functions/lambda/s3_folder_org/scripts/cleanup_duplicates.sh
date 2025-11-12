#!/bin/bash

set -e

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
AWS_PROFILE="${AWS_PROFILE:-default}"

echo "====================================================================="
echo "S3 Bucket Cleanup - Remove Duplicate Buckets"
echo "====================================================================="
echo ""

echo "Finding all batch buckets..."
# Get all batch buckets and group by batch number
aws s3 ls --profile $AWS_PROFILE | grep "batch-" | awk '{print $3}' > /tmp/all_buckets.txt

# Count total buckets
TOTAL_BUCKETS=$(wc -l < /tmp/all_buckets.txt)
echo "Found $TOTAL_BUCKETS total batch buckets"
echo ""

# Group buckets by batch number and keep only the first one of each
echo "Identifying buckets to keep (one per batch number)..."

# Create a file to store buckets we want to keep
> /tmp/keep_buckets.txt

# For each batch number, keep only the first bucket
for i in {1..29}; do
    FIRST_BUCKET=$(grep "^batch-$i-" /tmp/all_buckets.txt | head -1)
    if [ -n "$FIRST_BUCKET" ]; then
        echo "$FIRST_BUCKET" >> /tmp/keep_buckets.txt
        echo "  Keeping: $FIRST_BUCKET (for batch-$i)"
    fi
done

echo ""
echo "====================================================================="
echo "Buckets to DELETE:"
echo "====================================================================="

DELETE_COUNT=0
while IFS= read -r bucket; do
    # Check if this bucket is in the keep list
    if ! grep -q "^$bucket$" /tmp/keep_buckets.txt; then
        echo "  - $bucket"
        DELETE_COUNT=$((DELETE_COUNT + 1))
    fi
done < /tmp/all_buckets.txt

KEEP_COUNT=$(wc -l < /tmp/keep_buckets.txt)
echo ""
echo "Total buckets to delete: $DELETE_COUNT"
echo "Total buckets to keep: $KEEP_COUNT"
echo ""

# Ask for confirmation
read -p "Do you want to proceed with deletion? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deletion cancelled."
    rm /tmp/all_buckets.txt
    exit 0
fi

echo ""
echo "====================================================================="
echo "Deleting duplicate buckets..."
echo "====================================================================="

DELETED=0
while IFS= read -r bucket; do
    # If this bucket is NOT in the keep list, delete it
    if ! grep -q "^$bucket$" /tmp/keep_buckets.txt; then
        echo "Deleting: $bucket"

        # First, delete all objects in the bucket
        aws s3 rm s3://$bucket --recursive --profile $AWS_PROFILE --quiet

        # Then delete the bucket itself
        aws s3 rb s3://$bucket --profile $AWS_PROFILE

        DELETED=$((DELETED + 1))
        echo "  ✓ Deleted ($DELETED/$DELETE_COUNT)"
    fi
done < /tmp/all_buckets.txt

# Cleanup
rm /tmp/all_buckets.txt
rm /tmp/keep_buckets.txt

echo ""
echo "====================================================================="
echo "✓ Cleanup Complete!"
echo "====================================================================="
echo "Deleted: $DELETED buckets"
echo "Remaining: $KEEP_COUNT buckets (one per batch)"
echo ""
echo "To verify, run:"
echo "aws s3 ls --profile $AWS_PROFILE | grep batch-"
