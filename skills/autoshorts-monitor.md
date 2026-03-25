---
name: autoshorts-monitor
description: AutoShorts pipeline status monitoring -- heartbeat checks, error detection, report review
---

# AutoShorts Monitor

Monitor the pipeline's health and detect anomalies before they become problems.

## Check Items

### 1. Pipeline Health

```bash
autoshorts pipeline heartbeat
```

| Status | Meaning | Action |
|--------|---------|--------|
| `"status": "idle"` | No pipeline running, last run completed | Normal |
| `"status": "running"` | Pipeline currently executing | Normal, check `current_stage` |
| `"status": "failed"` | A stage has failed | Investigate immediately |

If `"healthy": false`, check the `error` field and refer to troubleshooting.

### 2. Validation Report

```bash
autoshorts validate report
```

| Metric | Threshold | Action |
|--------|-----------|--------|
| `rejection_rate` < 0.5 | Green | Normal operation |
| `rejection_rate` 0.5 - 0.8 | Yellow | Strategy auto-adjusting, monitor next cycle |
| `rejection_rate` > 0.8 | Red | Manual intervention needed |

Check `top_reasons` to understand what is being filtered:
- `already_on_youtube` high -- System should shift to newer/less-popular videos
- `license_unclear` high -- System should prefer CC-licensed creators
- `brand_detected` high -- System should favor outdoor/nature keywords

### 3. Upload Status

```bash
autoshorts upload status
```

| Check | Expected | Warning |
|-------|----------|---------|
| All platforms uploading | Yes | Any platform showing 0 uploads |
| Error count | 0-2 per day | More than 5 errors on any platform |
| Daily limit respected | 1-2 per channel | Exceeding limits risks account issues |

### 4. Stage 3 Review Queue

```bash
ls data/final/*/validation_final.json 2>/dev/null | xargs grep '"action": "openclaw_review"' 2>/dev/null | wc -l
```

If count > 0, manual review is pending. Use the `autoshorts-operator` skill to handle reviews.

## Anomaly Detection

### Pipeline not running when it should

If heartbeat shows `idle` during scheduled run times (09:00, 14:00, 19:00):

```bash
# Check cron is set up
crontab -l | grep autoshorts

# Check recent pipeline logs
tail -20 data/logs/pipeline.log
```

### Sudden spike in rejections

If rejection rate jumps from normal (<50%) to high (>80%) in one cycle:

```bash
# Compare today's report with yesterday's
autoshorts validate report
cat data/daily_reports/$(date -v-1d +%Y-%m-%d).json | python -m json.tool
```

Possible causes:
- A platform changed its content structure
- The crawler is hitting a different content segment
- A new type of content is being collected that fails validation

### Zero collections

If `autoshorts collector status` shows 0 for today:

```bash
# Test connectivity
autoshorts collector run --platform douyin --limit 5
```

If this also fails, see Playwright troubleshooting in `docs/openclaw-guide/troubleshooting.md`.

## Regular Monitoring Schedule

| Time | Check | Command |
|------|-------|---------|
| Continuous | Heartbeat | `autoshorts pipeline heartbeat` (via cron) |
| After each pipeline run | Validation report | `autoshorts validate report` |
| Evening | Upload status | `autoshorts upload status` |
| Evening | Review queue | Check for `openclaw_review` items |
| Weekly | Strategy trends | Compare daily reports over the week |
| Weekly | Storage | `du -sh data/` |
