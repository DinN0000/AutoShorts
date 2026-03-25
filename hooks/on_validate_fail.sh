#!/bin/bash
# Hook: on_validate_fail
# Trigger: A validation stage failed
# Action: Log rejection; for Stage 2 failures, retry editing up to 3 times
# Args: $1=stage (source|transform|final), $2=video_id, $3=reason

set -euo pipefail

STAGE="${1:-}"
VIDEO_ID="${2:-}"
REASON="${3:-unknown}"
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"

echo "[$(date)] Validation FAILED: stage=$STAGE video=$VIDEO_ID reason=$REASON" >> "$LOG_DIR/hooks.log"
echo "[$(date)] REJECTED: $VIDEO_ID (stage=$STAGE, reason=$REASON)" >> "data/rejection.log"

# Stage 2 (transform) failure: retry editing with stronger transforms (max 3 retries)
if [ "$STAGE" = "transform" ]; then
    RETRY_FILE="data/edited/$VIDEO_ID/retry_count"
    RETRY_COUNT=0

    if [ -f "$RETRY_FILE" ]; then
        RETRY_COUNT=$(cat "$RETRY_FILE")
    fi

    if [ "$RETRY_COUNT" -lt 3 ]; then
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "$RETRY_COUNT" > "$RETRY_FILE"
        echo "[$(date)] Retrying edit for $VIDEO_ID (attempt $RETRY_COUNT/3)" >> "$LOG_DIR/hooks.log"
        autoshorts edit --retry "$VIDEO_ID"
    else
        echo "[$(date)] Max retries reached for $VIDEO_ID. Discarding." >> "$LOG_DIR/hooks.log"
    fi
fi
