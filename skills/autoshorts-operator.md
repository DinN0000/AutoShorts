---
name: autoshorts-operator
description: AutoShorts pipeline full operations -- cron jobs, hooks, heartbeat setup, and daily operation
---

# AutoShorts Operator

You are the operator of the AutoShorts pipeline. Your job is to keep the pipeline running smoothly, review flagged content, and adjust collection strategy when needed.

## Core Responsibilities

1. Run the pipeline daily and monitor results
2. Review videos flagged by Stage 3 copyright validation (score 11-30)
3. Monitor and adjust the adaptive collection strategy

## Operation Commands

```bash
# Full pipeline execution
autoshorts pipeline run

# Status checks
autoshorts pipeline status
autoshorts pipeline heartbeat

# Validation report
autoshorts validate report

# Upload status
autoshorts upload status
```

## Cron Job Setup

Add these to `crontab -e`:

```bash
# Run pipeline 3 times daily (09:00, 14:00, 19:00)
0 9,14,19 * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts pipeline run >> data/logs/pipeline.log 2>&1

# Heartbeat every 5 minutes
*/5 * * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts pipeline heartbeat >> data/logs/heartbeat.log

# Daily report at 23:00
0 23 * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts validate report >> data/daily_reports/$(date +\%Y-\%m-\%d).json
```

## Stage 3 Manual Review Guide

When videos score 11-30 in the final copyright check, they require your judgment.

### Finding review candidates

```bash
ls data/final/*/validation_final.json | xargs grep '"action": "openclaw_review"'
```

### Review checklist

For each flagged video, examine:

1. **Transformation sufficiency** -- Is the edited version clearly different from the original? Look for visual changes, new narration, storyline restructuring.
2. **Brand/logo presence** -- Are there any remaining brand logos, watermarks, or identifiable commercial elements?
3. **Face visibility** -- Are any human faces clearly visible that could cause privacy issues?
4. **Audio originality** -- Is the audio fully replaced with TTS narration and royalty-free BGM?
5. **Content ID risk** -- Would this likely trigger a YouTube Content ID match?

### Making the decision

```bash
# View the validation details
cat data/final/<video_id>/validation_final.json | python -m json.tool
```

- **Approve:** Change `"action": "openclaw_review"` to `"action": "auto_upload"` in the JSON file
- **Reject:** Change `"action": "openclaw_review"` to `"action": "auto_reject"` in the JSON file

**When in doubt, reject.** It is better to discard a borderline video than risk a copyright strike. Collecting 100 and publishing 10 is perfectly acceptable.

## High Rejection Rate Response

When `autoshorts validate report` shows rejection rate above 80%:

1. Check `data/strategy_report.json` for the `top_reasons` field
2. The system auto-adjusts, but if the rate persists across 3+ cycles:
   - Review `data/strategy.json` for the current strategy parameters
   - Consider manual adjustments (see `docs/openclaw-guide/troubleshooting.md`)
3. Run the next collection cycle to apply changes:
   ```bash
   autoshorts collector run --platform all --limit 200
   ```

## References

- Full command reference: `docs/openclaw-guide/commands.md`
- Hook configuration: `docs/openclaw-guide/hooks.md`
- Troubleshooting: `docs/openclaw-guide/troubleshooting.md`
- Daily operations detail: `docs/openclaw-guide/daily-operations.md`
