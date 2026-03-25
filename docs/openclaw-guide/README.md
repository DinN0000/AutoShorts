# AutoShorts — OpenClaw Operation Guide

Read this document to operate the AutoShorts pipeline. No other context is needed.

## System Overview

AutoShorts is an automated pipeline that collects animal short videos from Chinese SNS platforms (Douyin, Kuaishou, Bilibili, Xiaohongshu), validates copyright compliance through a 3-stage loop, transforms them into original content with AI narration and visual effects, translates to 9 languages, and uploads to 6 platforms (YouTube, TikTok, Instagram, Facebook, Threads, Snapchat). All operations are CLI commands; you only need to run commands and review results.

## Quick Start

### 1. Run full pipeline once

```bash
autoshorts pipeline run
```

### 2. Check current status

```bash
autoshorts pipeline status
```

### 3. Heartbeat check (register as cron job)

```bash
autoshorts pipeline heartbeat
```

## Core Commands

| Command | Description |
|---------|-------------|
| `autoshorts pipeline run` | Run full pipeline once |
| `autoshorts pipeline status` | Check current pipeline state |
| `autoshorts pipeline heartbeat` | Heartbeat check (JSON output) |
| `autoshorts collector run --platform all --limit 200` | Collect videos |
| `autoshorts validate source --input data/raw/<date>/` | Stage 1 validation |
| `autoshorts validate final --input data/edited/<date>/` | Stage 2+3 validation |
| `autoshorts validate report` | View validation report |
| `autoshorts upload status` | Check upload status |

## Hook Setup

Register the hook scripts in `hooks/` directory with Claude Code:

```json
{
  "hooks": {
    "on_collect_complete": "bash hooks/on_collect_complete.sh",
    "on_validate_pass": "bash hooks/on_validate_pass.sh",
    "on_validate_fail": "bash hooks/on_validate_fail.sh",
    "on_edit_complete": "bash hooks/on_edit_complete.sh",
    "on_upload_complete": "bash hooks/on_upload_complete.sh",
    "on_upload_fail": "bash hooks/on_upload_fail.sh"
  }
}
```

## Daily Routine

1. **Morning:** Run `autoshorts pipeline run`
2. **Monitoring:** Check `autoshorts pipeline heartbeat` periodically
3. **Evening:** Review today's results with `autoshorts validate report`
4. **Review required:** Stage 3 videos with score 11-30 need your manual judgment

## Cautions

- **Stage 3 manual review:** Videos scoring 11-30 in the final copyright check require your judgment. Score 0-10 auto-uploads; score 31+ auto-rejects.
- **Strategy monitoring:** Check `data/strategy_report.json` to ensure the adaptive collection strategy is working. If rejection rate exceeds 80%, manual intervention may be needed.
- **Daily limits:** Never exceed 1-2 uploads per channel per day. The system enforces this but verify via `autoshorts upload status`.

## Further Reading

- [commands.md](commands.md) -- Full CLI reference
- [hooks.md](hooks.md) -- Hook setup details
- [troubleshooting.md](troubleshooting.md) -- Problem resolution
- [daily-operations.md](daily-operations.md) -- Detailed daily routine
