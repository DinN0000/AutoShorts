# Troubleshooting Guide

## 1. High Rejection Rate (>80%)

**Symptom:** `autoshorts validate report` shows rejection rate above 80%.

**Cause:** The collection strategy is fetching videos with high copyright risk.

**Resolution:**

```bash
# Check current strategy report
autoshorts validate report

# The system auto-adjusts strategy based on rejection reasons.
# Run the next collection cycle to apply adjustments.
autoshorts collector run --platform all --limit 200
```

**If auto-adjustment is insufficient**, edit `data/strategy.json` manually:

```json
{
  "prefer_cc_creators": true,
  "prefer_recent": true,
  "prefer_outdoor": true,
  "prefer_unpopular": true,
  "avoid_keywords": ["brand_name", "commercial"]
}
```

- `prefer_cc_creators: true` -- Prioritize creators with CC licenses
- `prefer_recent: true` -- Target newer, less-distributed videos
- `prefer_outdoor: true` -- Favor outdoor/nature content (fewer logos)
- `prefer_unpopular: true` -- Avoid already-viral videos likely on YouTube

## 2. Transform Validation Failure (Stage 2)

**Symptom:** Stage 2 repeatedly returns "insufficient_transformation".

**Cause:** Edits are not different enough from the original.

**Resolution:**

```bash
# Auto-retry with stronger transforms (up to 3 attempts)
autoshorts edit --retry <video_id>
```

Each retry increases transformation intensity:
- Retry 1: Add more visual effects, stronger color grading
- Retry 2: Re-cut clip order, add zoom/pan animations
- Retry 3: Maximum transformation (heavy crop, speed changes, full re-narration)

If all 3 retries fail, the video is automatically discarded. This is expected behavior -- not every source video can be sufficiently transformed.

## 3. Upload Failure

**Symptom:** `autoshorts upload status` shows errors for one or more platforms.

**Common causes and solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| API quota exceeded | Error message mentions "quota" or "rate limit" | Wait until quota resets (usually midnight UTC). Check daily limits in `config/platforms.yaml`. |
| Authentication expired | Error message mentions "401" or "unauthorized" | Refresh API tokens in `config/secrets.yaml`. For YouTube, re-run OAuth flow. |
| Video format rejected | Error message mentions "format" or "codec" | Check FFmpeg output settings. Ensure H.264 codec, AAC audio, 9:16 aspect ratio. |
| Network timeout | Error message mentions "timeout" or "connection" | Retry the upload: `autoshorts upload --input data/final/<id>/ --platforms <platform>` |

```bash
# Check which uploads failed
autoshorts upload status

# Retry a specific upload
autoshorts upload --input data/final/<video_id>/ --platforms youtube
```

## 4. Pipeline Stuck

**Symptom:** `autoshorts pipeline status` shows a stage as `failed` or `running` for too long.

**Resolution:**

```bash
# Check current state
autoshorts pipeline status

# Inspect the state file for error details
cat data/pipeline_state.json | python -m json.tool

# Option A: Re-run the full pipeline (skips completed stages)
autoshorts pipeline run

# Option B: Reset state and start fresh
rm data/pipeline_state.json
autoshorts pipeline run
```

**If a specific stage is stuck:**

| Stuck Stage | Action |
|-------------|--------|
| `collect` | Check network, try single platform: `autoshorts collector run --platform douyin --limit 5` |
| `validate_source` | Check if `data/raw/` has valid video files |
| `edit` | Check FFmpeg installation: `ffmpeg -version` |
| `validate_transform` | Run `autoshorts validate final --input data/edited/<date>/` manually |
| `translate` | Check edge-tts: `python -c "import edge_tts"` |
| `upload` | Check API credentials, see "Upload Failure" above |

## 5. Playwright Crawling Failure

**Symptom:** Collection returns 0 videos. Error log shows "timeout" or "navigation failed".

**Resolution:**

```bash
# Step 1: Update Playwright browsers
playwright install

# Step 2: Test with a single platform, small limit
autoshorts collector run --platform douyin --limit 5

# Step 3: If a specific platform fails, disable it temporarily
# Edit config/platforms.yaml:
#   douyin:
#     enabled: false
```

**Common Playwright issues:**

| Issue | Solution |
|-------|----------|
| Browser binary missing | Run `playwright install` |
| Platform changed its DOM | Check for updates to the collector adapters |
| IP blocked / CAPTCHA | Use a different network or add delays between requests |
| Headless mode fails | Try with `--headed` flag for debugging |

**Verifying platform accessibility:**

```bash
# Quick check if platform is reachable
curl -s -o /dev/null -w "%{http_code}" https://www.douyin.com
# Expected: 200 or 302
```
