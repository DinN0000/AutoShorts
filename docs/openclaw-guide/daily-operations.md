# Daily Operations Guide

## Morning Routine (run once)

### 1. Execute the pipeline

```bash
autoshorts pipeline run
```

Expected output:

```
[Pipeline] Starting run: run_20260325_090000
[Collect] Collecting from all platforms (limit: 200)...
[Collect] Collected 187 videos
[Validate] Stage 1: 187 videos → 94 passed, 93 rejected
[Edit] Editing 94 videos...
[Edit] Completed 94 edits
[Validate] Stage 2: 94 videos → 78 passed, 16 rejected (12 retried)
[Validate] Stage 3: 78 videos → 61 auto-upload, 8 review, 9 rejected
[Translate] Translating 61 videos to 9 languages...
[Upload] Uploading to 6 platforms (scheduled)...
[Pipeline] Run complete. 8 videos need manual review.
```

### 2. Review yesterday's report

```bash
autoshorts validate report
```

Expected output:

```json
{
  "date": "2026-03-24",
  "total_collected": 543,
  "total_passed": 172,
  "rejection_rate": 0.68,
  "top_reasons": {
    "already_on_youtube": 142,
    "license_unclear": 98,
    "brand_detected": 71,
    "insufficient_quality": 60
  },
  "strategy_adjustments": [
    "prefer_recent: true (triggered by high already_on_youtube count)",
    "prefer_cc_creators: true (triggered by license_unclear count)"
  ]
}
```

Key checks:
- `rejection_rate` below 0.8 is acceptable
- Review `top_reasons` to understand what the system is filtering
- Confirm `strategy_adjustments` are reasonable

## Midday Monitoring

### Heartbeat check

```bash
autoshorts pipeline heartbeat
```

Expected output (healthy):

```json
{"status":"idle","run_id":"run_20260325_090000","current_stage":"none","healthy":true}
```

Expected output (running):

```json
{"status":"running","run_id":"run_20260325_140000","current_stage":"edit","healthy":true}
```

Warning output (problem):

```json
{"status":"failed","run_id":"run_20260325_140000","current_stage":"validate_transform","healthy":false,"error":"FFmpeg process crashed"}
```

If `healthy` is `false`, see [troubleshooting.md](troubleshooting.md).

## Evening Review

### 1. Check upload results

```bash
autoshorts upload status
```

Expected output:

```
Platform     | Uploaded | Failed | Scheduled
-------------|----------|--------|----------
YouTube      |       12 |      0 |         4
TikTok       |       12 |      1 |         3
Instagram    |       11 |      0 |         5
Facebook     |       12 |      0 |         4
Threads      |       10 |      2 |         4
Snapchat     |        8 |      0 |         6
```

### 2. Handle Stage 3 manual reviews

Check for videos that need your judgment:

```bash
ls data/final/*/validation_final.json | xargs grep '"action": "openclaw_review"'
```

For each flagged video, review the validation details:

```bash
cat data/final/<video_id>/validation_final.json | python -m json.tool
```

Decision criteria:
- Is the edited video sufficiently different from the original?
- Does the new narration/storyline add genuine value?
- Are there any remaining brand logos, faces, or copyrighted elements?
- Would this pass a YouTube Content ID check?

After review, update the action:

```bash
# To approve for upload:
# Change "action": "openclaw_review" to "action": "auto_upload" in validation_final.json

# To reject:
# Change "action": "openclaw_review" to "action": "auto_reject" in validation_final.json
```

## Weekly Review

Perform these checks once per week:

### Collection strategy health

```bash
autoshorts validate report
```

- Rejection rate trend: should be stable or decreasing
- If consistently above 50%, review the adaptive strategy adjustments
- Check if certain platforms are underperforming

### Upload performance

```bash
autoshorts upload status
```

- Verify all platforms are receiving uploads
- Check for recurring failures on any platform
- Confirm daily limits are being respected

### API quota check

- YouTube Data API: Check remaining quota in Google Cloud Console
- Other platforms: Verify API keys have not expired

### Storage cleanup

```bash
# Check data directory size
du -sh data/

# Old rejected videos can be safely removed
# (system does not re-process them)
```
