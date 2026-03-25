#!/bin/bash
# Hook: on_upload_fail
# Trigger: A video upload failed on a platform
# Action: Log the failure for manual investigation
# Args: $1=video_id, $2=platform, $3=error

set -euo pipefail

VIDEO_ID="${1:-}"
PLATFORM="${2:-}"
ERROR="${3:-unknown}"
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"

echo "[$(date)] Upload FAILED: video=$VIDEO_ID platform=$PLATFORM error=$ERROR" >> "$LOG_DIR/hooks.log"
