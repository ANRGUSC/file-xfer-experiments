#!/bin/bash

# =============================================================================
# Hourly SCP Speed Collector + Plot Generator
# =============================================================================

PROJECT_DIR="/Users/oliviacognetti/Downloads/Research/file-xfer-experiments"

cd "$PROJECT_DIR"

# Run data collection
/usr/bin/python3 scpSpeed1.py >> results/cron.log 2>&1

# Run plot generation
/usr/bin/python3 scpPlot1.py >> results/cron.log 2>&1

echo "$(date): Hourly run completed" >> results/cron.log
