#!/bin/bash
# Daily report generation — add to crontab: 0 23 * * *
DATE=$(date +%Y-%m-%d)
mkdir -p data/daily_reports
autoshorts validate report > "data/daily_reports/$DATE.json"
echo "[$(date)] Daily report generated: data/daily_reports/$DATE.json" >> data/logs/hooks.log
