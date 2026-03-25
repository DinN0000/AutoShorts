#!/bin/bash
# Hook: on_upload_complete
# Trigger: A video was successfully uploaded to a platform
# Action: Log the success
# Args: $1=video_id, $2=platform

set -euo pipefail

VIDEO_ID="${1:-}"
PLATFORM="${2:-}"
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"

echo "[$(date)] Upload SUCCESS: video=$VIDEO_ID platform=$PLATFORM" >> "$LOG_DIR/hooks.log"
