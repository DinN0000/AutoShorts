# CLI Command Reference

Complete reference for all AutoShorts CLI commands.

## collector

### `autoshorts collector run`

Collect animal videos from Chinese SNS platforms using Playwright.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--platform` | choice | `all` | Target platform: douyin, kuaishou, bilibili, xiaohongshu, all |
| `--limit` | int | `50` | Maximum number of videos to collect |

Output: Number of videos collected.
Data: `data/raw/{date}/{platform}_{id}/meta.json`

Example:

```bash
autoshorts collector run --platform douyin --limit 50
autoshorts collector run --platform all --limit 200
```

### `autoshorts collector status`

Show collection statistics grouped by date.

Output: Table of dates, platforms, counts.

```bash
autoshorts collector status
```

## validate

### `autoshorts validate source --input <path>`

Run Stage 1 source validation. Checks copyright safety of raw videos before editing.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--input` | path | Yes | Directory containing raw videos |

Output: Pass/reject counts, high rejection rate warning.
Data: Creates `validation_source.json` in each video directory.

Checks performed:
- License status (CC license, platform ToS)
- Duplicate detection (already on YouTube, same source used by others)
- Content classification (animal abuse filter, brand/logo/face detection)

```bash
autoshorts validate source --input data/raw/2026-03-25/
```

### `autoshorts validate final --input <path>`

Run Stage 2 (transformation sufficiency) + Stage 3 (final AI judgment) validation.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--input` | path | Yes | Directory containing edited videos |

Stage 2 checks:
- Change ratio vs original
- Narration/storyline additions
- Visual transformation degree
- Audio replacement (royalty-free BGM)
- Metadata quality (title, description, tags)

Stage 3 checks:
- Claude Vision comprehensive assessment
- Risk score assignment (0-10: auto-upload, 11-30: OpenClaw review, 31+: auto-reject)

```bash
autoshorts validate final --input data/edited/2026-03-25/
```

### `autoshorts validate report`

Display the contents of `data/strategy_report.json`. Shows rejection rate, top rejection reasons, and strategy adjustment history.

```bash
autoshorts validate report
```

## edit

### `autoshorts edit --input <path>`

Transform validated source videos into original content.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--input` | path | Yes | Directory containing validated source videos |

Processing pipeline:
1. Clip splitting and recombination
2. Speed variation (0.8x-1.2x random)
3. Color correction and filter application
4. Mirror, crop, zoom visual transforms
5. Original audio removal
6. Whisper STT on original audio
7. Claude generates new storyline from transcript

Output: `data/edited/{id}/`

```bash
autoshorts edit --input data/validated/source/video_001/
```

### `autoshorts edit --retry <id>`

Re-edit a video that failed Stage 2 validation with stronger transformations. Maximum 3 retries.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--retry` | string | Yes | Video ID to re-edit |

```bash
autoshorts edit --retry video_001
```

## translate

### `autoshorts translate --input <path> --langs <codes>`

Translate edited videos to multiple languages.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--input` | path | Yes | Edited video directory |
| `--langs` | string | Yes | Comma-separated language codes |

Processing:
- Claude translates storyline to each language
- edge-tts generates narration per language
- SRT subtitle files per language
- Localized title, description, hashtags per language

Output: `data/localized/{id}/{lang}/`

```bash
autoshorts translate --input data/edited/video_001/ --langs en,ja,de,ko,fr,es,pt,hi,ar
```

## upload

### `autoshorts upload --input <path> --platforms <names>`

Upload finalized videos to specified platforms.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--input` | path | Yes | Final video directory |
| `--platforms` | string | Yes | Comma-separated platforms |

Supported platforms: youtube, tiktok, instagram, facebook, threads, snapchat

Upload respects:
- Per-channel daily limits from `config/platforms.yaml`
- Primetime scheduling from `config/schedule.yaml`

```bash
autoshorts upload --input data/final/video_001/ --platforms youtube,tiktok,instagram,facebook,threads,snapchat
```

### `autoshorts upload status`

Show upload status across all platforms.

```bash
autoshorts upload status
```

### `autoshorts upload schedule`

Show optimal upload times per language based on target timezone primetime hours.

```bash
autoshorts upload schedule
```

## pipeline

### `autoshorts pipeline run`

Execute the full pipeline once: collect -> validate source -> edit -> validate transform -> translate -> validate final -> upload.

```bash
autoshorts pipeline run
```

### `autoshorts pipeline status`

Show current pipeline state as JSON. Includes run ID, current stage, and status of each stage.

```bash
autoshorts pipeline status
```

### `autoshorts pipeline heartbeat`

Output a single-line JSON with current pipeline health. Designed for cron job monitoring.

```bash
autoshorts pipeline heartbeat
```

Expected output:

```json
{"status":"idle","run_id":"run_20260325_090000","current_stage":"none","healthy":true}
```
