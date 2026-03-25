---
name: autoshorts-troubleshoot
description: AutoShorts fault response -- pipeline failures, crawling errors, upload failures, and recovery
---

# AutoShorts Troubleshoot

Use this skill when something goes wrong with the pipeline.

## Diagnostic Steps

### Step 1: Identify the problem

```bash
autoshorts pipeline status
```

Look at the output to determine which stage failed.

### Step 2: Check error details

```bash
cat data/pipeline_state.json | python -m json.tool
```

The `error` field in the failed stage will contain the error message.

### Step 3: Classify the problem

| Failed Stage | Problem Category | Jump To |
|-------------|-----------------|---------|
| `collect` | Crawling issue | [Crawling Failures](#crawling-failures) |
| `validate_source` | Validation logic error | [Validation Errors](#validation-errors) |
| `edit` | FFmpeg / video processing | [Editing Failures](#editing-failures) |
| `validate_transform` | Transform insufficient | [Transform Issues](#transform-issues) |
| `translate` | TTS / translation error | [Translation Failures](#translation-failures) |
| `validate_final` | Final check error | [Final Validation Issues](#final-validation-issues) |
| `upload` | API / network error | [Upload Failures](#upload-failures) |

## Crawling Failures

**Symptoms:** Collection returns 0 videos, timeout errors.

**Diagnostic commands:**

```bash
# Check if Playwright browsers are installed
playwright install --dry-run

# Test a single platform with minimal load
autoshorts collector run --platform douyin --limit 5

# Check network connectivity
curl -s -o /dev/null -w "%{http_code}" https://www.douyin.com
```

**Solutions:**

| Root Cause | Fix |
|-----------|-----|
| Browser binary missing | `playwright install` |
| Platform unreachable | Check network, VPN, or DNS settings |
| Platform DOM changed | Update the collector adapter for that platform |
| IP blocked / CAPTCHA | Switch network, add request delays |
| All platforms failing | Check system proxy settings, firewall |

**Temporary workaround:** Disable the failing platform in `config/platforms.yaml`:

```yaml
douyin:
  enabled: false  # Temporarily disabled
```

## Validation Errors

**Symptoms:** `validate_source` stage fails with an exception (not high rejection rate, which is normal).

```bash
# Check validation output for the specific date
ls data/raw/$(date +%Y-%m-%d)/*/validation_source.json

# Look for error entries
grep -l '"error"' data/raw/$(date +%Y-%m-%d)/*/validation_source.json
```

**Solutions:**

| Root Cause | Fix |
|-----------|-----|
| Malformed meta.json | Check the collector output, re-collect |
| Missing video file | Ensure download completed; re-collect |
| Claude API error | Check API subscription status |

## Editing Failures

**Symptoms:** `edit` stage fails, FFmpeg errors in logs.

```bash
# Verify FFmpeg is installed and working
ffmpeg -version

# Check if Whisper model is available
python -c "import whisper; print(whisper.available_models())"

# Try editing a single video
autoshorts edit --input data/validated/source/<video_id>/
```

**Solutions:**

| Root Cause | Fix |
|-----------|-----|
| FFmpeg not installed | `brew install ffmpeg` (macOS) |
| FFmpeg codec error | Check input video codec compatibility |
| Whisper model missing | `python -c "import whisper; whisper.load_model('base')"` |
| Disk space full | Clean old data: `du -sh data/*` and remove rejected videos |

## Transform Issues

**Symptoms:** Stage 2 validation repeatedly fails with "insufficient_transformation".

This is usually not an error but a content quality issue. The system handles it automatically:

1. First failure: Auto-retry with stronger effects
2. Second failure: Auto-retry with maximum transformation
3. Third failure: Video is discarded

```bash
# Check retry count for a video
cat data/edited/<video_id>/retry_count

# Manually trigger a retry
autoshorts edit --retry <video_id>
```

If many videos are failing Stage 2, the source material may not be suitable for transformation. Check the collection strategy.

## Translation Failures

**Symptoms:** `translate` stage fails, TTS generation errors.

```bash
# Test edge-tts
python -c "import edge_tts; print('edge-tts OK')"

# Test with a specific language
python -c "
import asyncio, edge_tts
async def test():
    c = edge_tts.Communicate('Hello world', 'en-US-AriaNeural')
    await c.save('/tmp/test_tts.mp3')
asyncio.run(test())
print('TTS test passed')
"
```

**Solutions:**

| Root Cause | Fix |
|-----------|-----|
| edge-tts not installed | `pip install edge-tts` |
| Voice not available | Check voice name in `config/languages.yaml` |
| Network error (edge-tts needs internet) | Check connectivity |
| Claude translation error | Check API status, retry |

## Final Validation Issues

**Symptoms:** Stage 3 fails with an exception (not rejection, which is normal).

```bash
# Check if Claude Vision API is accessible
# Stage 3 uses Claude Vision for frame sampling
autoshorts validate final --input data/edited/<date>/
```

**Solutions:**

| Root Cause | Fix |
|-----------|-----|
| Claude API quota | Check subscription status |
| Frame extraction failed | Verify FFmpeg can extract frames from the video |
| Malformed validation input | Check that Stage 2 output is complete |

## Upload Failures

**Symptoms:** `upload` stage fails or `autoshorts upload status` shows errors.

```bash
# Check upload status for details
autoshorts upload status

# Retry a specific upload
autoshorts upload --input data/final/<video_id>/ --platforms <platform>
```

**Solutions:**

| Root Cause | Fix |
|-----------|-----|
| YouTube API quota exceeded | Wait for quota reset (midnight Pacific). Check [Google Cloud Console](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas). |
| OAuth token expired | Re-authenticate: check `config/secrets.yaml` |
| Video too long/short | Check platform requirements (YouTube Shorts: max 60s) |
| Rate limited | Reduce `daily_limit_per_channel` in `config/platforms.yaml` |
| Platform API down | Check platform status page, retry later |

## Full Pipeline Reset

When nothing else works:

```bash
# 1. Check current state
autoshorts pipeline status

# 2. Reset pipeline state (does not delete data)
rm data/pipeline_state.json

# 3. Re-run from scratch
autoshorts pipeline run
```

**Warning:** This re-runs all stages. Already-uploaded videos will not be re-uploaded (the system tracks upload state per video).

## Detailed Guides

For step-by-step resolution of specific problems, see `docs/openclaw-guide/troubleshooting.md`.
