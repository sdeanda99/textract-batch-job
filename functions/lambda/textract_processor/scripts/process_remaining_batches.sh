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

# Get start batch from argument (default to 2 if not specified)
START_BATCH="${1:-2}"

echo "====================================================================="
echo "Processing Batches $START_BATCH-$TOTAL_BATCHES"
echo "====================================================================="
echo ""

if [ "$START_BATCH" -gt "$TOTAL_BATCHES" ]; then
    echo "Error: Start batch ($START_BATCH) is greater than total batches ($TOTAL_BATCHES)"
    exit 1
fi

for i in $(seq $START_BATCH $TOTAL_BATCHES); do
    echo "-------------------------------------------------------------------"
    echo "Processing Batch $i of $TOTAL_BATCHES"
    echo "-------------------------------------------------------------------"

    ./05_process_batches.sh $i

    if [ $i -lt $TOTAL_BATCHES ]; then
        echo ""
        echo "Waiting 60 seconds before next batch..."
        sleep 60
    fi
done

echo ""
echo "====================================================================="
echo "✓ All Batches ($START_BATCH-$TOTAL_BATCHES) Initiated!"
echo "====================================================================="
echo ""
echo "Usage: $0 [start_batch_number]"
echo "  Default: Start from batch 2 (assumes batch 1 already processed)"
echo "  Example: $0 5  # Start from batch 5"
echo ""
