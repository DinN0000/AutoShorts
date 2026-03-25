#!/bin/bash
# Edit complete → Start Stage 2 transform validation
VIDEO_ID=$1
echo "[$(date)] Edit complete: video=$VIDEO_ID — starting transform validation" >> data/logs/hooks.log
autoshorts validate final --input "data/edited/$VIDEO_ID/"
