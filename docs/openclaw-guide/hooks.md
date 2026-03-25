# Hook Setup Guide

Hooks automate the pipeline by triggering the next step when a stage completes. All hook scripts live in the `hooks/` directory.

## Hook List

| Hook | Trigger | Action |
|------|---------|--------|
| `on_collect_complete` | Collection finished | Start Stage 1 source validation |
| `on_validate_pass` | Validation passed | Route to next stage (edit or upload) |
| `on_validate_fail` | Validation failed | Log rejection, update strategy report, retry if Stage 2 |
| `on_edit_complete` | Editing finished | Start Stage 2 transform validation |
| `on_upload_complete` | Upload succeeded | Log success to upload report |
| `on_upload_fail` | Upload failed | Log failure, alert for manual check |
| `heartbeat` | Every 5 minutes (cron) | Check pipeline health |
| `daily_report` | Daily at 23:00 (cron) | Generate daily operations report |

## Hook Scripts

### hooks/on_collect_complete.sh

Triggers source validation on newly collected videos.

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
echo "[$(date)] Collection complete. Starting source validation..." >> data/logs/hooks.log
autoshorts validate source --input "data/raw/$DATE/"
```

### hooks/on_validate_pass.sh

Routes the video to the next pipeline stage based on which validation stage passed.

```bash
#!/bin/bash
STAGE=$1  # source, transform, final
VIDEO_ID=$2
echo "[$(date)] Validation PASSED: stage=$STAGE video=$VIDEO_ID" >> data/logs/hooks.log

case $STAGE in
  source)
    autoshorts edit --input "data/validated/$VIDEO_ID/"
    ;;
  transform)
    autoshorts translate --input "data/edited/$VIDEO_ID/" --langs en,ja,de,ko,fr,es,pt
    ;;
  final)
    autoshorts upload --input "data/final/$VIDEO_ID/" --platforms youtube,tiktok,instagram,facebook,threads,snapchat
    ;;
esac
```

### hooks/on_validate_fail.sh

Logs the rejection and retries editing for Stage 2 failures (up to 3 times).

```bash
#!/bin/bash
STAGE=$1
VIDEO_ID=$2
REASON=$3
echo "[$(date)] Validation FAILED: stage=$STAGE video=$VIDEO_ID reason=$REASON" >> data/logs/hooks.log

# Stage 2 failure: retry editing with stronger transforms (max 3)
if [ "$STAGE" = "transform" ]; then
  RETRY_COUNT=$(cat "data/edited/$VIDEO_ID/retry_count" 2>/dev/null || echo 0)
  if [ "$RETRY_COUNT" -lt 3 ]; then
    echo $((RETRY_COUNT + 1)) > "data/edited/$VIDEO_ID/retry_count"
    autoshorts edit --retry "$VIDEO_ID"
  fi
fi
```

### hooks/on_upload_complete.sh

```bash
#!/bin/bash
VIDEO_ID=$1
PLATFORM=$2
echo "[$(date)] Upload SUCCESS: video=$VIDEO_ID platform=$PLATFORM" >> data/logs/hooks.log
```

### hooks/on_upload_fail.sh

```bash
#!/bin/bash
VIDEO_ID=$1
PLATFORM=$2
ERROR=$3
echo "[$(date)] Upload FAILED: video=$VIDEO_ID platform=$PLATFORM error=$ERROR" >> data/logs/hooks.log
```

## Cron Jobs

### Heartbeat (every 5 minutes)

```bash
*/5 * * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts pipeline heartbeat >> data/logs/heartbeat.log
```

### Daily report (23:00 daily)

```bash
0 23 * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts validate report >> data/daily_reports/$(date +\%Y-\%m-\%d).json
```

## Claude Code Hook Configuration

Add the following to your Claude Code `settings.json` to wire hooks into the tool execution lifecycle:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "autoshorts collector run",
        "command": "bash hooks/on_collect_complete.sh"
      },
      {
        "matcher": "autoshorts edit --input",
        "command": "bash hooks/on_edit_complete.sh"
      }
    ]
  }
}
```

For the full list of hooks and their triggers, register each hook script as appropriate for your automation setup. The scripts accept positional arguments (stage, video ID, reason/platform/error) and append structured log lines to `data/logs/hooks.log`.
