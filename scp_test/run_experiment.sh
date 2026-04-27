#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"
TERRAFORM=/opt/homebrew/bin/terraform

mkdir -p "$LOG_DIR"

exec >> "$LOG_FILE" 2>&1

echo "=== Run started at $(date) ==="

cd "$SCRIPT_DIR"

RUN_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "--- terraform apply (run: $RUN_TIMESTAMP) ---"
$TERRAFORM apply -auto-approve -var="run_timestamp=$RUN_TIMESTAMP"

echo "--- terraform destroy ---"
$TERRAFORM destroy -auto-approve -var="run_timestamp=$RUN_TIMESTAMP"

echo "=== Run completed at $(date) ==="
