#!/bin/bash

# =============================================================================
# SCP Speed Collector - Cron Wrapper Script
# =============================================================================
# EDIT THE PATH BELOW to match your project directory location
# =============================================================================

PROJECT_DIR="/path/to/your/file-xfer-experiments"  # <-- EDIT THIS LINE

# =============================================================================
# Do not edit below this line
# =============================================================================

cd "$PROJECT_DIR"
/usr/bin/python3 scpSpeed.py >> results/cron.log 2>&1
