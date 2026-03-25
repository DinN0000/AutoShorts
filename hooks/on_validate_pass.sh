#!/bin/bash
# Hook: on_validate_pass
# Trigger: A validation stage passed
# Action: Route the video to the next pipeline stage
# Args: $1=stage (source|transform|final), $2=video_id

set -euo pipefail

STAGE="${1:-}"
VIDEO_ID="${2:-}"
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"

echo "[$(date)] Validation PASSED: stage=$STAGE video=$VIDEO_ID" >> "$LOG_DIR/hooks.log"

case "$STAGE" in
  source)
    autoshorts edit --input "data/validated/$VIDEO_ID/"
    ;;
  transform)
    autoshorts translate --input "data/edited/$VIDEO_ID/" --langs en,ja,de,ko,fr,es,pt,hi,ar
    ;;
  final)
    autoshorts upload --input "data/final/$VIDEO_ID/" --platforms youtube,tiktok,instagram,facebook,threads,snapchat
    ;;
  *)
    echo "[$(date)] WARNING: Unknown validation stage '$STAGE' for video=$VIDEO_ID" >> "$LOG_DIR/hooks.log"
    ;;
esac
