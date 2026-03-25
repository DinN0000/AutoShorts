#!/bin/bash
# Hook: on_collect_complete
# Trigger: Collection stage finished
# Action: Start Stage 1 source validation on today's collected videos

set -euo pipefail

DATE=$(date +%Y-%m-%d)
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"

echo "[$(date)] Collection complete. Starting source validation..." >> "$LOG_DIR/hooks.log"

if [ -d "data/raw/$DATE" ]; then
    autoshorts validate source --input "data/raw/$DATE/"
    echo "[$(date)] Source validation triggered for data/raw/$DATE/" >> "$LOG_DIR/hooks.log"
else
    echo "[$(date)] WARNING: No raw data directory found for $DATE" >> "$LOG_DIR/hooks.log"
fi
