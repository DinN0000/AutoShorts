import json
from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """AutoShorts - Automated animal shorts pipeline."""
    pass


@main.group()
def collector():
    """Collect animal videos from Chinese SNS platforms."""
    pass


@main.group()
def validate():
    """Validate videos for copyright compliance."""
    pass


@main.command()
@click.option("--input", "input_dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--retry", "retry_id", type=str, default=None)
def edit(input_dir: Path, retry_id: str | None):
    """Edit videos with transformative changes."""
    click.echo("Edit — not yet implemented")


@main.command()
@click.option("--input", "input_dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--langs", type=str, default="en,ko,ja")
def translate(input_dir: Path, langs: str):
    """Translate and localize videos to multiple languages."""
    import asyncio
    from autoshorts.translator.runner import translate_and_localize
    from autoshorts.common.storage import DIRS, ensure_dirs

    ensure_dirs()
    lang_list = [l.strip() for l in langs.split(",")]
    click.echo(f"Translating to {len(lang_list)} languages: {', '.join(lang_list)}")

    # Look for text files in input directory to translate
    text_files = list(input_dir.glob("*.txt"))
    if not text_files:
        click.echo("No text files found in input directory.")
        return

    for text_file in text_files:
        text = text_file.read_text(encoding="utf-8")
        video_id = text_file.stem
        click.echo(f"Processing: {video_id}")

        for lang in lang_list:
            output_dir = DIRS["localized"] / video_id / lang
            try:
                result = asyncio.run(
                    translate_and_localize(text, lang, str(output_dir))
                )
                click.echo(f"  {lang}: SRT={result['srt_path']}")
            except Exception as e:
                click.echo(f"  {lang}: FAILED — {e}", err=True)

    click.echo("Translation complete.")


@main.group()
def upload():
    """Upload videos to multiple platforms."""
    pass


@main.group()
def pipeline():
    """Orchestrate the full pipeline."""
    pass


# --- Collector subcommands ---

@collector.command()
@click.option("--platform", type=click.Choice(["douyin", "kuaishou", "bilibili", "xiaohongshu", "all"]), default="all")
@click.option("--limit", type=int, default=50)
def run(platform: str, limit: int):
    """Collect videos from specified platform(s)."""
    import asyncio
    from autoshorts.collector.base import PlatformAdapter
    from autoshorts.collector.douyin import DouyinAdapter
    from autoshorts.collector.bilibili import BilibiliAdapter
    from autoshorts.collector.kuaishou import KuaishouAdapter
    from autoshorts.collector.xiaohongshu import XiaohongshuAdapter
    from autoshorts.collector.runner import CollectorRunner
    from autoshorts.common.storage import DIRS, ensure_dirs

    ensure_dirs()
    all_adapters: dict[str, PlatformAdapter] = {
        "douyin": DouyinAdapter(),
        "kuaishou": KuaishouAdapter(),
        "bilibili": BilibiliAdapter(),
        "xiaohongshu": XiaohongshuAdapter(),
    }

    if platform == "all":
        adapters = list(all_adapters.values())
    else:
        adapters = [all_adapters[platform]]

    runner = CollectorRunner(adapters)
    results = asyncio.run(runner.collect(DIRS["raw"], limit))
    click.echo(f"Collected {len(results)} videos")


@collector.command()
def status():
    """Show collection status."""
    from autoshorts.common.storage import DIRS
    raw_dir = DIRS["raw"]
    if not raw_dir.exists():
        click.echo("No collections yet.")
        return
    dates = sorted(d.name for d in raw_dir.iterdir() if d.is_dir())
    for d in dates:
        count = sum(1 for _ in (raw_dir / d).iterdir() if (raw_dir / d).is_dir())
        click.echo(f"  {d}: {count} videos")


# --- Validate subcommands ---

@validate.command()
@click.option("--input", "input_dir", type=click.Path(exists=True, path_type=Path), required=True)
def source(input_dir: Path):
    """Run Stage 1 source validation."""
    from autoshorts.validator.runner import validate_source, generate_rejection_stats
    results = validate_source(input_dir)
    passed = sum(1 for r in results if r.passed)
    click.echo(f"Validated {len(results)} videos: {passed} passed, {len(results) - passed} rejected")

    stats = generate_rejection_stats(results)
    rejection_rate = stats["rejected"] / stats["total"] if stats["total"] > 0 else 0
    if rejection_rate > 0.5:
        click.echo(f"WARNING: High rejection rate ({rejection_rate:.0%})")
        top_reasons = stats.get("common_reasons", {})
        if top_reasons:
            top = max(top_reasons, key=top_reasons.get)
            click.echo(f"Top reason: {top}")


@validate.command()
@click.option("--input", "input_dir", type=click.Path(exists=True, path_type=Path), required=True)
def final(input_dir: Path):
    """Run Stage 2+3 final validation."""
    click.echo("Final validation — not yet implemented")


@validate.command()
def report():
    """Show validation statistics."""
    report_path = Path("data/strategy_report.json")
    if not report_path.exists():
        click.echo("No report available yet.")
        return
    data = json.loads(report_path.read_text())
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


# --- Upload subcommands ---

@upload.command("run")
@click.option("--input", "input_dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--platforms", type=str, default="youtube")
def upload_run(input_dir: Path, platforms: str):
    """Upload videos to specified platforms."""
    click.echo("Upload — not yet implemented")


@upload.command("status")
def upload_status():
    """Show upload status."""
    click.echo("Upload status — not yet implemented")


@upload.command()
def schedule():
    """Show optimal upload schedule per language."""
    from autoshorts.uploader.scheduler import TIMEZONE_MAP
    for lang, info in TIMEZONE_MAP.items():
        country, _, prime_start, prime_end = info
        click.echo(f"  {lang}: {country} primetime {prime_start}:00-{prime_end}:00")


# --- Pipeline subcommands ---

@pipeline.command("run")
def pipeline_run():
    """Run the full pipeline once."""
    from autoshorts.pipeline.runner import run_pipeline
    try:
        state = run_pipeline()
        click.echo(f"Pipeline {state.run_id} completed successfully")
    except Exception as e:
        click.echo(f"Pipeline failed: {e}", err=True)


@pipeline.command()
def status():
    """Show current pipeline status."""
    from autoshorts.pipeline.runner import get_status
    click.echo(json.dumps(get_status(), indent=2, ensure_ascii=False))


@pipeline.command()
def heartbeat():
    """Heartbeat check for OpenClaw monitoring."""
    from autoshorts.pipeline.runner import get_status
    status_data = get_status()
    click.echo(json.dumps(status_data))
