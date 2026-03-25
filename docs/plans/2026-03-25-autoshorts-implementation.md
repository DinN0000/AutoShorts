# AutoShorts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an automated pipeline that collects animal shorts from Chinese SNS, validates copyright compliance through a 3-stage loop, edits videos into transformative content, translates to multiple languages, and uploads to 6 platforms — all orchestrated by OpenClaw via CLI.

**Architecture:** Modular CLI-based pipeline with 6 independent agents (collector, validator, editor, translator, uploader, pipeline). Each agent is a Python module invokable via `python -m autoshorts <command>`. State is passed between agents via JSON files in `data/`. OpenClaw controls the pipeline through hooks, cron jobs, and heartbeat checks.

**Tech Stack:** Python 3.11+, Playwright (crawling), FFmpeg/MoviePy (video), Whisper (STT), edge-tts (TTS), Claude subscription tokens (AI analysis/generation), YouTube Data API v3, Click (CLI)

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/autoshorts/__init__.py`
- Create: `src/autoshorts/__main__.py`
- Create: `src/autoshorts/cli.py`
- Create: `.gitignore`
- Create: `CLAUDE.md`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "autoshorts"
version = "0.1.0"
description = "Automated animal shorts pipeline with copyright-safe multi-platform publishing"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
    "rich>=13.0",
]

[project.optional-dependencies]
collector = ["playwright>=1.40"]
editor = ["moviepy>=1.0", "openai-whisper>=20231117"]
translator = ["edge-tts>=6.1"]
uploader = [
    "google-api-python-client>=2.100",
    "google-auth-oauthlib>=1.1",
]
dev = ["pytest>=7.4", "pytest-asyncio>=0.21"]
all = ["autoshorts[collector,editor,translator,uploader,dev]"]

[project.scripts]
autoshorts = "autoshorts.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/autoshorts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**Step 2: Create directory structure**

```bash
mkdir -p src/autoshorts/{collector,validator,editor,translator,uploader,pipeline,common}
mkdir -p tests/{collector,validator,editor,translator,uploader,pipeline}
mkdir -p config data/{raw,validated,edited,localized,final,uploads}
mkdir -p docs/{openclaw-guide,architecture,modules,setup}
mkdir -p skills hooks
```

**Step 3: Create .gitignore**

```gitignore
# Data (large video files, not for git)
data/

# Python
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
venv/

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Secrets
.env
config/secrets.yaml
```

**Step 4: Create CLAUDE.md**

```markdown
# AutoShorts

Automated animal shorts pipeline: collect → validate → edit → translate → upload.

## Commands

- `autoshorts collector run --platform <name> --limit <n>` - Collect videos
- `autoshorts validate source --input <path>` - Stage 1 validation
- `autoshorts validate final --input <path>` - Stage 2+3 validation
- `autoshorts edit --input <path>` - Edit video
- `autoshorts translate --input <path> --langs <codes>` - Translate
- `autoshorts upload --input <path> --platforms <names>` - Upload
- `autoshorts pipeline run` - Run full pipeline

## Rules

- When modifying a module, update its corresponding doc in `docs/modules/`
- All copyright validation logic lives in `src/autoshorts/validator/`
- Never skip validation stages — the 3-stage loop is the core safety mechanism
- Data files go in `data/` (gitignored), config in `config/`
- Test with `pytest`
```

**Step 5: Create src/autoshorts/__init__.py**

```python
"""AutoShorts - Automated animal shorts pipeline."""
```

**Step 6: Create src/autoshorts/__main__.py**

```python
from autoshorts.cli import main

main()
```

**Step 7: Write the failing test for CLI**

```python
# tests/test_cli.py
from click.testing import CliRunner
from autoshorts.cli import main


def test_cli_shows_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "autoshorts" in result.output.lower() or "Usage" in result.output
```

**Step 8: Run test to verify it fails**

Run: `cd /Users/hwaa/Developer/AutoShorts && python -m pytest tests/test_cli.py -v`
Expected: FAIL (module not found)

**Step 9: Create src/autoshorts/cli.py**

```python
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


@main.group()
def edit():
    """Edit videos with transformative changes."""
    pass


@main.group()
def translate():
    """Translate and localize videos to multiple languages."""
    pass


@main.group()
def upload():
    """Upload videos to multiple platforms."""
    pass


@main.group()
def pipeline():
    """Orchestrate the full pipeline."""
    pass
```

**Step 10: Run test to verify it passes**

Run: `cd /Users/hwaa/Developer/AutoShorts && pip install -e ".[dev]" && python -m pytest tests/test_cli.py -v`
Expected: PASS

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with CLI entry point"
```

---

## Task 2: Common Data Models

**Files:**
- Create: `src/autoshorts/common/models.py`
- Create: `src/autoshorts/common/__init__.py`
- Create: `src/autoshorts/common/storage.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py
import json
from pathlib import Path
from autoshorts.common.models import VideoMeta, ValidationResult, VideoStatus


def test_video_meta_creation():
    meta = VideoMeta(
        id="douyin_abc123",
        platform="douyin",
        source_url="https://example.com/video/abc123",
        title="Cute cat playing",
        author="user123",
        duration_seconds=45,
        tags=["cat", "cute"],
    )
    assert meta.id == "douyin_abc123"
    assert meta.platform == "douyin"
    assert meta.status == VideoStatus.RAW


def test_video_meta_to_json(tmp_path):
    meta = VideoMeta(
        id="test_001",
        platform="bilibili",
        source_url="https://example.com",
        title="Test",
        author="author",
        duration_seconds=30,
    )
    path = tmp_path / "meta.json"
    meta.save(path)
    loaded = VideoMeta.load(path)
    assert loaded.id == "test_001"
    assert loaded.platform == "bilibili"


def test_validation_result():
    result = ValidationResult(
        video_id="test_001",
        stage="source",
        passed=False,
        score=65,
        reasons=["brand_logo_detected", "already_on_youtube"],
    )
    assert not result.passed
    assert "brand_logo_detected" in result.reasons
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL (import error)

**Step 3: Create src/autoshorts/common/__init__.py**

```python
"""Common utilities and data models."""
```

**Step 4: Implement models**

```python
# src/autoshorts/common/models.py
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime


class VideoStatus(str, Enum):
    RAW = "raw"
    SOURCE_VALIDATED = "source_validated"
    EDITED = "edited"
    TRANSFORM_VALIDATED = "transform_validated"
    FINAL_VALIDATED = "final_validated"
    LOCALIZED = "localized"
    UPLOADED = "uploaded"
    REJECTED = "rejected"


@dataclass
class VideoMeta:
    id: str
    platform: str
    source_url: str
    title: str
    author: str
    duration_seconds: float
    tags: list[str] = field(default_factory=list)
    status: VideoStatus = VideoStatus.RAW
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    license_info: str = ""
    rejection_reason: str = ""

    def save(self, path: Path) -> None:
        data = asdict(self)
        data["status"] = self.status.value
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> VideoMeta:
        data = json.loads(path.read_text())
        data["status"] = VideoStatus(data["status"])
        return cls(**data)


@dataclass
class ValidationResult:
    video_id: str
    stage: str  # "source", "transform", "final"
    passed: bool
    score: int  # 0-100, lower is safer
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> ValidationResult:
        return cls(**json.loads(path.read_text()))
```

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS

**Step 6: Create storage utility**

```python
# src/autoshorts/common/storage.py
from pathlib import Path

DATA_DIR = Path("data")

DIRS = {
    "raw": DATA_DIR / "raw",
    "validated": DATA_DIR / "validated",
    "edited": DATA_DIR / "edited",
    "localized": DATA_DIR / "localized",
    "final": DATA_DIR / "final",
    "uploads": DATA_DIR / "uploads",
}


def ensure_dirs() -> None:
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)


def video_dir(stage: str, video_id: str, date: str | None = None) -> Path:
    base = DIRS[stage]
    if date:
        base = base / date
    path = base / video_id
    path.mkdir(parents=True, exist_ok=True)
    return path
```

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add common data models and storage utilities"
```

---

## Task 3: Collector — Platform Adapters

**Files:**
- Create: `src/autoshorts/collector/__init__.py`
- Create: `src/autoshorts/collector/base.py`
- Create: `src/autoshorts/collector/douyin.py`
- Create: `src/autoshorts/collector/bilibili.py`
- Create: `src/autoshorts/collector/kuaishou.py`
- Create: `src/autoshorts/collector/xiaohongshu.py`
- Create: `src/autoshorts/collector/strategy.py`
- Create: `src/autoshorts/collector/runner.py`
- Test: `tests/collector/test_strategy.py`
- Test: `tests/collector/test_base.py`

**Step 1: Write the failing test for base adapter**

```python
# tests/collector/__init__.py
```

```python
# tests/collector/test_base.py
from autoshorts.collector.base import PlatformAdapter, CollectResult


def test_collect_result_creation():
    result = CollectResult(
        video_id="douyin_123",
        platform="douyin",
        source_url="https://example.com/123",
        title="Cute cat",
        author="user1",
        duration_seconds=30,
        video_path=None,
        metadata={"likes": 1000},
        license_info="unknown",
    )
    assert result.video_id == "douyin_123"


def test_platform_adapter_is_abstract():
    try:
        adapter = PlatformAdapter()
        assert False, "Should not instantiate abstract class"
    except TypeError:
        pass
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collector/test_base.py -v`
Expected: FAIL

**Step 3: Implement base adapter**

```python
# src/autoshorts/collector/__init__.py
"""Video collector module."""
```

```python
# src/autoshorts/collector/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CollectResult:
    video_id: str
    platform: str
    source_url: str
    title: str
    author: str
    duration_seconds: float
    video_path: Path | None
    metadata: dict = field(default_factory=dict)
    license_info: str = "unknown"


class PlatformAdapter(ABC):
    """Base class for platform-specific crawlers."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        ...

    @abstractmethod
    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        ...

    @abstractmethod
    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        ...
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/collector/test_base.py -v`
Expected: PASS

**Step 5: Write the failing test for strategy engine**

```python
# tests/collector/test_strategy.py
import json
from autoshorts.collector.strategy import (
    SearchStrategy,
    StrategyEngine,
    RejectionStats,
)


def test_default_strategy():
    strategy = SearchStrategy.default()
    assert len(strategy.keywords) > 0
    assert strategy.prefer_recent is True


def test_strategy_engine_adjusts_on_high_rejection(tmp_path):
    engine = StrategyEngine(data_dir=tmp_path)

    stats = RejectionStats(
        total_collected=100,
        total_rejected=85,
        reasons={"already_on_youtube": 40, "license_unclear": 30, "brand_logo": 15},
    )

    strategy = SearchStrategy.default()
    adjusted = engine.adjust(strategy, stats)

    # High rejection rate (85%) should trigger strategy change
    assert adjusted != strategy
    assert adjusted.prefer_recent is True  # Should shift to recent/unpopular


def test_strategy_engine_no_change_on_low_rejection(tmp_path):
    engine = StrategyEngine(data_dir=tmp_path)

    stats = RejectionStats(
        total_collected=100,
        total_rejected=30,
        reasons={"brand_logo": 20, "license_unclear": 10},
    )

    strategy = SearchStrategy.default()
    adjusted = engine.adjust(strategy, stats)

    # Low rejection rate (30%) should keep strategy
    assert adjusted.keywords == strategy.keywords
```

**Step 6: Run test to verify it fails**

Run: `python -m pytest tests/collector/test_strategy.py -v`
Expected: FAIL

**Step 7: Implement strategy engine**

```python
# src/autoshorts/collector/strategy.py
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class SearchStrategy:
    keywords: list[str] = field(default_factory=list)
    prefer_recent: bool = True
    prefer_unpopular: bool = False
    prefer_outdoor: bool = False
    prefer_cc_creators: bool = False
    platform_weights: dict[str, float] = field(default_factory=dict)

    @classmethod
    def default(cls) -> SearchStrategy:
        return cls(
            keywords=[
                "可爱动物", "搞笑宠物", "猫咪日常", "狗狗搞笑",
                "动物萌宠", "宠物日常", "cute animal", "funny pet",
                "小猫", "小狗", "兔子", "仓鼠",
            ],
            prefer_recent=True,
            platform_weights={
                "douyin": 0.3,
                "kuaishou": 0.25,
                "bilibili": 0.25,
                "xiaohongshu": 0.2,
            },
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> SearchStrategy:
        return cls(**json.loads(path.read_text()))


@dataclass
class RejectionStats:
    total_collected: int
    total_rejected: int
    reasons: dict[str, int] = field(default_factory=dict)

    @property
    def rejection_rate(self) -> float:
        if self.total_collected == 0:
            return 0.0
        return self.total_rejected / self.total_collected

    @property
    def top_reason(self) -> str | None:
        if not self.reasons:
            return None
        return max(self.reasons, key=self.reasons.get)


REASON_ADJUSTMENTS: dict[str, dict[str, bool]] = {
    "already_on_youtube": {"prefer_recent": True, "prefer_unpopular": True},
    "license_unclear": {"prefer_cc_creators": True},
    "brand_logo": {"prefer_outdoor": True},
}


class StrategyEngine:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.report_path = data_dir / "strategy_report.json"

    def adjust(self, current: SearchStrategy, stats: RejectionStats) -> SearchStrategy:
        if stats.rejection_rate < 0.5:
            return current

        adjusted = SearchStrategy(
            keywords=list(current.keywords),
            prefer_recent=current.prefer_recent,
            prefer_unpopular=current.prefer_unpopular,
            prefer_outdoor=current.prefer_outdoor,
            prefer_cc_creators=current.prefer_cc_creators,
            platform_weights=dict(current.platform_weights),
        )

        for reason, count in sorted(stats.reasons.items(), key=lambda x: -x[1]):
            if reason in REASON_ADJUSTMENTS:
                for attr, value in REASON_ADJUSTMENTS[reason].items():
                    setattr(adjusted, attr, value)

        self._save_report(stats, adjusted)
        return adjusted

    def _save_report(self, stats: RejectionStats, adjusted: SearchStrategy) -> None:
        report = {
            "rejection_rate": stats.rejection_rate,
            "top_reasons": dict(
                sorted(stats.reasons.items(), key=lambda x: -x[1])[:5]
            ),
            "adjustments_applied": asdict(adjusted),
        }
        self.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
```

**Step 8: Run test to verify it passes**

Run: `python -m pytest tests/collector/test_strategy.py -v`
Expected: PASS

**Step 9: Create platform adapter stubs**

Each platform adapter follows the same pattern. Implement Douyin as the reference, others follow.

```python
# src/autoshorts/collector/douyin.py
from __future__ import annotations

from pathlib import Path

from autoshorts.collector.base import PlatformAdapter, CollectResult


class DouyinAdapter(PlatformAdapter):
    """Douyin (抖音) video collector."""

    @property
    def platform_name(self) -> str:
        return "douyin"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        # TODO: Implement Playwright-based Douyin search
        # 1. Navigate to Douyin search
        # 2. Search each keyword
        # 3. Filter by animal/pet category
        # 4. Extract video metadata
        raise NotImplementedError("Douyin adapter not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        # TODO: Download video using Playwright
        raise NotImplementedError("Douyin download not yet implemented")
```

```python
# src/autoshorts/collector/bilibili.py
from __future__ import annotations

from pathlib import Path

from autoshorts.collector.base import PlatformAdapter, CollectResult


class BilibiliAdapter(PlatformAdapter):
    @property
    def platform_name(self) -> str:
        return "bilibili"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        raise NotImplementedError("Bilibili adapter not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        raise NotImplementedError("Bilibili download not yet implemented")
```

```python
# src/autoshorts/collector/kuaishou.py
from __future__ import annotations

from pathlib import Path

from autoshorts.collector.base import PlatformAdapter, CollectResult


class KuaishouAdapter(PlatformAdapter):
    @property
    def platform_name(self) -> str:
        return "kuaishou"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        raise NotImplementedError("Kuaishou adapter not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        raise NotImplementedError("Kuaishou download not yet implemented")
```

```python
# src/autoshorts/collector/xiaohongshu.py
from __future__ import annotations

from pathlib import Path

from autoshorts.collector.base import PlatformAdapter, CollectResult


class XiaohongshuAdapter(PlatformAdapter):
    @property
    def platform_name(self) -> str:
        return "xiaohongshu"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        raise NotImplementedError("Xiaohongshu adapter not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        raise NotImplementedError("Xiaohongshu download not yet implemented")
```

**Step 10: Create collector runner and wire CLI**

```python
# src/autoshorts/collector/runner.py
from __future__ import annotations

import asyncio
from pathlib import Path
from datetime import date

from autoshorts.collector.base import PlatformAdapter, CollectResult
from autoshorts.collector.douyin import DouyinAdapter
from autoshorts.collector.bilibili import BilibiliAdapter
from autoshorts.collector.kuaishou import KuaishouAdapter
from autoshorts.collector.xiaohongshu import XiaohongshuAdapter
from autoshorts.collector.strategy import SearchStrategy, StrategyEngine
from autoshorts.common.models import VideoMeta, VideoStatus
from autoshorts.common.storage import video_dir, ensure_dirs


ADAPTERS: dict[str, type[PlatformAdapter]] = {
    "douyin": DouyinAdapter,
    "kuaishou": KuaishouAdapter,
    "bilibili": BilibiliAdapter,
    "xiaohongshu": XiaohongshuAdapter,
}


async def collect(platform: str, limit: int, strategy_path: Path | None = None) -> list[VideoMeta]:
    ensure_dirs()

    if strategy_path and strategy_path.exists():
        strategy = SearchStrategy.load(strategy_path)
    else:
        strategy = SearchStrategy.default()

    platforms = list(ADAPTERS.keys()) if platform == "all" else [platform]
    results: list[VideoMeta] = []
    today = date.today().isoformat()

    for plat in platforms:
        adapter = ADAPTERS[plat]()
        per_platform_limit = limit // len(platforms)

        collected = await adapter.search(strategy.keywords, per_platform_limit)

        for item in collected:
            out_dir = video_dir("raw", item.video_id, today)
            video_path = await adapter.download(item, out_dir)

            meta = VideoMeta(
                id=item.video_id,
                platform=plat,
                source_url=item.source_url,
                title=item.title,
                author=item.author,
                duration_seconds=item.duration_seconds,
                tags=list(item.metadata.get("tags", [])),
                license_info=item.license_info,
            )
            meta.save(out_dir / "meta.json")
            results.append(meta)

    return results
```

**Step 11: Wire collector CLI commands**

Update `src/autoshorts/cli.py` — add under the collector group:

```python
@collector.command()
@click.option("--platform", type=click.Choice(["douyin", "kuaishou", "bilibili", "xiaohongshu", "all"]), default="all")
@click.option("--limit", type=int, default=50)
def run(platform: str, limit: int):
    """Collect videos from specified platform(s)."""
    import asyncio
    from autoshorts.collector.runner import collect
    results = asyncio.run(collect(platform, limit))
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
```

**Step 12: Commit**

```bash
git add -A
git commit -m "feat: add collector module with platform adapters and adaptive strategy"
```

---

## Task 4: Validator — Stage 1 (Source Validation)

**Files:**
- Create: `src/autoshorts/validator/__init__.py`
- Create: `src/autoshorts/validator/stage1.py`
- Create: `src/autoshorts/validator/checks.py`
- Test: `tests/validator/__init__.py`
- Test: `tests/validator/test_stage1.py`

**Step 1: Write the failing test**

```python
# tests/validator/test_stage1.py
from autoshorts.validator.stage1 import SourceValidator
from autoshorts.common.models import VideoMeta


def test_rejects_video_with_brand_logo():
    meta = VideoMeta(
        id="test_001",
        platform="douyin",
        source_url="https://example.com",
        title="Cat in Nike store",
        author="user1",
        duration_seconds=30,
        tags=["nike", "cat"],
    )

    validator = SourceValidator()
    # Simulating brand detection in metadata
    result = validator.check_metadata(meta)
    assert not result.passed
    assert "brand_detected" in result.reasons


def test_accepts_clean_video():
    meta = VideoMeta(
        id="test_002",
        platform="douyin",
        source_url="https://example.com",
        title="野外小猫玩耍",
        author="catlovers",
        duration_seconds=25,
        tags=["cat", "outdoor", "cute"],
        license_info="cc-by",
    )

    validator = SourceValidator()
    result = validator.check_metadata(meta)
    assert result.passed


def test_rejects_too_short_video():
    meta = VideoMeta(
        id="test_003",
        platform="douyin",
        source_url="https://example.com",
        title="Quick cat",
        author="user1",
        duration_seconds=3,
    )

    validator = SourceValidator()
    result = validator.check_metadata(meta)
    assert not result.passed
    assert "too_short" in result.reasons
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/validator/test_stage1.py -v`
Expected: FAIL

**Step 3: Implement checks module**

```python
# src/autoshorts/validator/__init__.py
"""Video validation module — 3-stage copyright compliance."""
```

```python
# src/autoshorts/validator/checks.py
"""Individual validation checks."""
from __future__ import annotations

from autoshorts.common.models import VideoMeta

BRAND_KEYWORDS = [
    "nike", "adidas", "gucci", "prada", "louis vuitton", "chanel",
    "coca cola", "pepsi", "mcdonalds", "starbucks", "apple", "samsung",
    "disney", "marvel", "pokemon", "nintendo",
]

DANGEROUS_KEYWORDS = [
    "虐待", "abuse", "fight", "打架", "受伤", "hurt", "cruelty",
]

MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 180


def check_brands(meta: VideoMeta) -> tuple[bool, list[str]]:
    text = f"{meta.title} {' '.join(meta.tags)}".lower()
    found = [b for b in BRAND_KEYWORDS if b in text]
    if found:
        return False, [f"brand_detected:{','.join(found)}"]
    return True, []


def check_dangerous_content(meta: VideoMeta) -> tuple[bool, list[str]]:
    text = f"{meta.title} {' '.join(meta.tags)}".lower()
    found = [d for d in DANGEROUS_KEYWORDS if d in text]
    if found:
        return False, [f"dangerous_content:{','.join(found)}"]
    return True, []


def check_duration(meta: VideoMeta) -> tuple[bool, list[str]]:
    if meta.duration_seconds < MIN_DURATION_SECONDS:
        return False, ["too_short"]
    if meta.duration_seconds > MAX_DURATION_SECONDS:
        return False, ["too_long"]
    return True, []


def check_license(meta: VideoMeta) -> tuple[bool, list[str]]:
    safe_licenses = ["cc-by", "cc-by-sa", "cc0", "public_domain"]
    if meta.license_info.lower() in safe_licenses:
        return True, ["license_verified"]
    # Unknown license is not an auto-reject, but adds score
    return True, []
```

**Step 4: Implement Stage 1 validator**

```python
# src/autoshorts/validator/stage1.py
from __future__ import annotations

from autoshorts.common.models import VideoMeta, ValidationResult
from autoshorts.validator.checks import (
    check_brands,
    check_dangerous_content,
    check_duration,
    check_license,
)


class SourceValidator:
    """Stage 1: Validate raw collected videos before editing."""

    def check_metadata(self, meta: VideoMeta) -> ValidationResult:
        reasons: list[str] = []
        score = 0

        # Duration check
        ok, msgs = check_duration(meta)
        if not ok:
            reasons.extend(msgs)
            score += 100  # Auto-reject

        # Brand check
        ok, msgs = check_brands(meta)
        if not ok:
            reasons.extend(msgs)
            score += 50

        # Dangerous content check
        ok, msgs = check_dangerous_content(meta)
        if not ok:
            reasons.extend(msgs)
            score += 100  # Auto-reject

        # License check (bonus for known good license)
        ok, msgs = check_license(meta)
        if "license_verified" in msgs:
            score = max(0, score - 20)

        # Unknown license adds risk
        if not meta.license_info:
            score += 10
            reasons.append("license_unknown")

        passed = score < 31

        return ValidationResult(
            video_id=meta.id,
            stage="source",
            passed=passed,
            score=min(score, 100),
            reasons=reasons,
        )
```

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/validator/test_stage1.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add Stage 1 source validator with brand, content, and license checks"
```

---

## Task 5: Validator — Stage 2 (Transform Validation) & Stage 3 (Final)

**Files:**
- Create: `src/autoshorts/validator/stage2.py`
- Create: `src/autoshorts/validator/stage3.py`
- Create: `src/autoshorts/validator/runner.py`
- Test: `tests/validator/test_stage2.py`
- Test: `tests/validator/test_stage3.py`

**Step 1: Write failing test for Stage 2**

```python
# tests/validator/test_stage2.py
from autoshorts.validator.stage2 import TransformValidator, EditManifest


def test_rejects_insufficient_transformation():
    manifest = EditManifest(
        video_id="test_001",
        original_duration=30.0,
        edited_duration=30.0,
        has_narration=False,
        has_new_storyline=False,
        visual_changes=["subtitles_added"],
        audio_replaced=False,
        bgm_source="unknown",
    )
    validator = TransformValidator()
    result = validator.check(manifest)
    assert not result.passed
    assert "insufficient_transformation" in result.reasons


def test_accepts_high_transformation():
    manifest = EditManifest(
        video_id="test_002",
        original_duration=30.0,
        edited_duration=28.0,
        has_narration=True,
        has_new_storyline=True,
        visual_changes=["speed_change", "color_grade", "crop", "flip", "zoom"],
        audio_replaced=True,
        bgm_source="royalty_free",
    )
    validator = TransformValidator()
    result = validator.check(manifest)
    assert result.passed


def test_rejects_unknown_bgm_source():
    manifest = EditManifest(
        video_id="test_003",
        original_duration=30.0,
        edited_duration=25.0,
        has_narration=True,
        has_new_storyline=True,
        visual_changes=["speed_change", "color_grade", "crop"],
        audio_replaced=True,
        bgm_source="unknown",
    )
    validator = TransformValidator()
    result = validator.check(manifest)
    assert not result.passed
    assert "bgm_not_royalty_free" in result.reasons
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/validator/test_stage2.py -v`
Expected: FAIL

**Step 3: Implement Stage 2**

```python
# src/autoshorts/validator/stage2.py
from __future__ import annotations

from dataclasses import dataclass, field
from autoshorts.common.models import ValidationResult

SAFE_BGM_SOURCES = ["royalty_free", "original", "tts_only", "none"]
MIN_VISUAL_CHANGES = 3


@dataclass
class EditManifest:
    video_id: str
    original_duration: float
    edited_duration: float
    has_narration: bool
    has_new_storyline: bool
    visual_changes: list[str]
    audio_replaced: bool
    bgm_source: str
    metadata_title: str = ""
    metadata_description: str = ""
    credit_included: bool = True


class TransformValidator:
    """Stage 2: Verify edited video is sufficiently transformative."""

    def check(self, manifest: EditManifest) -> ValidationResult:
        reasons: list[str] = []
        score = 0

        # Transformation sufficiency
        transform_score = 0
        if manifest.has_narration:
            transform_score += 3
        if manifest.has_new_storyline:
            transform_score += 3
        if manifest.audio_replaced:
            transform_score += 2
        transform_score += min(len(manifest.visual_changes), 5)

        if transform_score < 6:
            reasons.append("insufficient_transformation")
            score += 50

        # BGM copyright
        if manifest.audio_replaced and manifest.bgm_source not in SAFE_BGM_SOURCES:
            reasons.append("bgm_not_royalty_free")
            score += 40

        # Visual changes count
        if len(manifest.visual_changes) < MIN_VISUAL_CHANGES:
            reasons.append("too_few_visual_changes")
            score += 20

        passed = score < 31
        return ValidationResult(
            video_id=manifest.video_id,
            stage="transform",
            passed=passed,
            score=min(score, 100),
            reasons=reasons,
        )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/validator/test_stage2.py -v`
Expected: PASS

**Step 5: Write failing test for Stage 3**

```python
# tests/validator/test_stage3.py
from autoshorts.validator.stage3 import FinalValidator, FinalCheckInput


def test_auto_upload_low_score():
    check = FinalCheckInput(
        video_id="test_001",
        risk_score=5,
        risk_reasons=[],
    )
    validator = FinalValidator()
    result = validator.check(check)
    assert result.passed
    assert result.details["action"] == "auto_upload"


def test_manual_review_mid_score():
    check = FinalCheckInput(
        video_id="test_002",
        risk_score=20,
        risk_reasons=["slight_similarity_detected"],
    )
    validator = FinalValidator()
    result = validator.check(check)
    assert result.passed  # passes but needs review
    assert result.details["action"] == "openclaw_review"


def test_auto_reject_high_score():
    check = FinalCheckInput(
        video_id="test_003",
        risk_score=55,
        risk_reasons=["high_similarity", "potential_reupload"],
    )
    validator = FinalValidator()
    result = validator.check(check)
    assert not result.passed
    assert result.details["action"] == "auto_reject"
```

**Step 6: Run test to verify it fails**

Run: `python -m pytest tests/validator/test_stage3.py -v`
Expected: FAIL

**Step 7: Implement Stage 3**

```python
# src/autoshorts/validator/stage3.py
from __future__ import annotations

from dataclasses import dataclass, field
from autoshorts.common.models import ValidationResult


@dataclass
class FinalCheckInput:
    video_id: str
    risk_score: int  # 0-100, from Claude Vision analysis
    risk_reasons: list[str] = field(default_factory=list)


class FinalValidator:
    """Stage 3: Final validation before upload using Claude Vision scoring."""

    AUTO_UPLOAD_THRESHOLD = 10
    REVIEW_THRESHOLD = 30

    def check(self, check_input: FinalCheckInput) -> ValidationResult:
        score = check_input.risk_score

        if score <= self.AUTO_UPLOAD_THRESHOLD:
            action = "auto_upload"
            passed = True
        elif score <= self.REVIEW_THRESHOLD:
            action = "openclaw_review"
            passed = True  # passes but flagged for review
        else:
            action = "auto_reject"
            passed = False

        return ValidationResult(
            video_id=check_input.video_id,
            stage="final",
            passed=passed,
            score=score,
            reasons=check_input.risk_reasons,
            details={"action": action},
        )
```

**Step 8: Run test to verify it passes**

Run: `python -m pytest tests/validator/test_stage3.py -v`
Expected: PASS

**Step 9: Create validator runner and wire CLI**

```python
# src/autoshorts/validator/runner.py
from __future__ import annotations

from pathlib import Path
import json

from autoshorts.common.models import VideoMeta, ValidationResult
from autoshorts.common.storage import DIRS
from autoshorts.validator.stage1 import SourceValidator
from autoshorts.validator.stage2 import TransformValidator
from autoshorts.validator.stage3 import FinalValidator
from autoshorts.collector.strategy import RejectionStats


def validate_source(input_dir: Path) -> list[ValidationResult]:
    """Run Stage 1 validation on all raw videos in input_dir."""
    validator = SourceValidator()
    results: list[ValidationResult] = []

    for video_dir in sorted(input_dir.iterdir()):
        if not video_dir.is_dir():
            continue
        meta_path = video_dir / "meta.json"
        if not meta_path.exists():
            continue

        meta = VideoMeta.load(meta_path)
        result = validator.check_metadata(meta)
        result.save(video_dir / "validation_source.json")
        results.append(result)

    return results


def generate_rejection_stats(results: list[ValidationResult]) -> RejectionStats:
    """Aggregate rejection reasons for strategy adjustment."""
    rejected = [r for r in results if not r.passed]
    reason_counts: dict[str, int] = {}
    for r in rejected:
        for reason in r.reasons:
            key = reason.split(":")[0]  # Normalize "brand_detected:nike" → "brand_detected"
            reason_counts[key] = reason_counts.get(key, 0) + 1

    return RejectionStats(
        total_collected=len(results),
        total_rejected=len(rejected),
        reasons=reason_counts,
    )
```

**Step 10: Wire validate CLI commands in cli.py**

```python
@validate.command()
@click.option("--input", "input_dir", type=click.Path(exists=True, path_type=Path), required=True)
def source(input_dir: Path):
    """Run Stage 1 source validation."""
    from autoshorts.validator.runner import validate_source, generate_rejection_stats
    results = validate_source(input_dir)
    passed = sum(1 for r in results if r.passed)
    click.echo(f"Validated {len(results)} videos: {passed} passed, {len(results) - passed} rejected")

    stats = generate_rejection_stats(results)
    if stats.rejection_rate > 0.5:
        click.echo(f"WARNING: High rejection rate ({stats.rejection_rate:.0%})")
        click.echo(f"Top reason: {stats.top_reason}")


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
```

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: add 3-stage validator with source, transform, and final checks"
```

---

## Task 6: Editor Module

**Files:**
- Create: `src/autoshorts/editor/__init__.py`
- Create: `src/autoshorts/editor/transforms.py`
- Create: `src/autoshorts/editor/narration.py`
- Create: `src/autoshorts/editor/runner.py`
- Test: `tests/editor/__init__.py`
- Test: `tests/editor/test_transforms.py`

**Step 1: Write the failing test**

```python
# tests/editor/test_transforms.py
from autoshorts.editor.transforms import build_ffmpeg_filters, EditConfig


def test_build_filters_with_all_transforms():
    config = EditConfig(
        speed_factor=1.2,
        flip_horizontal=True,
        crop_percent=0.1,
        color_brightness=0.05,
        color_contrast=1.1,
        color_saturation=1.2,
    )
    filters = build_ffmpeg_filters(config)
    assert "setpts=" in filters  # speed change
    assert "hflip" in filters  # horizontal flip
    assert "crop=" in filters  # crop
    assert "eq=" in filters  # color adjustment


def test_build_filters_minimal():
    config = EditConfig(speed_factor=1.0)
    filters = build_ffmpeg_filters(config)
    # No speed change at 1.0x
    assert "setpts=" not in filters or "1.0" in filters


def test_edit_config_visual_changes_list():
    config = EditConfig(
        speed_factor=1.2,
        flip_horizontal=True,
        crop_percent=0.1,
    )
    changes = config.visual_changes()
    assert "speed_change" in changes
    assert "flip" in changes
    assert "crop" in changes
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/editor/test_transforms.py -v`
Expected: FAIL

**Step 3: Implement transforms**

```python
# src/autoshorts/editor/__init__.py
"""Video editor module."""
```

```python
# src/autoshorts/editor/transforms.py
from __future__ import annotations

from dataclasses import dataclass, field
import random


@dataclass
class EditConfig:
    speed_factor: float = 1.0
    flip_horizontal: bool = False
    crop_percent: float = 0.0
    color_brightness: float = 0.0
    color_contrast: float = 1.0
    color_saturation: float = 1.0
    zoom_factor: float = 1.0

    def visual_changes(self) -> list[str]:
        changes = []
        if self.speed_factor != 1.0:
            changes.append("speed_change")
        if self.flip_horizontal:
            changes.append("flip")
        if self.crop_percent > 0:
            changes.append("crop")
        if self.color_brightness != 0 or self.color_contrast != 1.0 or self.color_saturation != 1.0:
            changes.append("color_grade")
        if self.zoom_factor != 1.0:
            changes.append("zoom")
        return changes

    @classmethod
    def random_strong(cls) -> EditConfig:
        """Generate a random config with strong transformations."""
        return cls(
            speed_factor=random.uniform(0.8, 1.2),
            flip_horizontal=random.choice([True, False]),
            crop_percent=random.uniform(0.05, 0.15),
            color_brightness=random.uniform(-0.1, 0.1),
            color_contrast=random.uniform(0.9, 1.3),
            color_saturation=random.uniform(0.8, 1.4),
            zoom_factor=random.uniform(1.0, 1.15),
        )


def build_ffmpeg_filters(config: EditConfig) -> str:
    filters: list[str] = []

    if config.speed_factor != 1.0:
        pts = 1.0 / config.speed_factor
        filters.append(f"setpts={pts:.4f}*PTS")

    if config.flip_horizontal:
        filters.append("hflip")

    if config.crop_percent > 0:
        pct = config.crop_percent
        filters.append(f"crop=iw*{1-pct:.2f}:ih*{1-pct:.2f}")

    if config.color_brightness != 0 or config.color_contrast != 1.0 or config.color_saturation != 1.0:
        filters.append(
            f"eq=brightness={config.color_brightness:.2f}"
            f":contrast={config.color_contrast:.2f}"
            f":saturation={config.color_saturation:.2f}"
        )

    if config.zoom_factor != 1.0:
        z = config.zoom_factor
        filters.append(f"zoompan=z={z:.2f}:d=1:s=1080x1920")

    return ",".join(filters)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/editor/test_transforms.py -v`
Expected: PASS

**Step 5: Create narration module stub**

```python
# src/autoshorts/editor/narration.py
from __future__ import annotations

from pathlib import Path


async def transcribe_audio(video_path: Path) -> str:
    """Use Whisper to transcribe audio from video."""
    # TODO: Implement with openai-whisper
    # import whisper
    # model = whisper.load_model("base")
    # result = model.transcribe(str(video_path))
    # return result["text"]
    raise NotImplementedError("Whisper transcription not yet implemented")


async def generate_storyline(original_text: str) -> str:
    """Use Claude (subscription) to generate a new storyline from original transcript."""
    # TODO: Implement with Claude subscription token
    # This creates a completely new narrative based on what the video shows
    raise NotImplementedError("Storyline generation not yet implemented")
```

**Step 6: Create editor runner**

```python
# src/autoshorts/editor/runner.py
from __future__ import annotations

import subprocess
from pathlib import Path
from dataclasses import asdict

from autoshorts.editor.transforms import EditConfig, build_ffmpeg_filters
from autoshorts.validator.stage2 import EditManifest


def edit_video(
    input_video: Path,
    output_dir: Path,
    config: EditConfig | None = None,
    narration_text: str = "",
) -> EditManifest:
    """Apply transformative edits to a video using FFmpeg."""
    if config is None:
        config = EditConfig.random_strong()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "edited.mp4"

    filters = build_ffmpeg_filters(config)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-an",  # Remove original audio
    ]

    if filters:
        cmd.extend(["-vf", filters])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        str(output_path),
    ])

    subprocess.run(cmd, check=True, capture_output=True)

    # Get duration from ffprobe
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(input_video)],
        capture_output=True, text=True,
    )
    original_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

    probe2 = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True,
    )
    edited_duration = float(probe2.stdout.strip()) if probe2.stdout.strip() else 0

    manifest = EditManifest(
        video_id=output_dir.name,
        original_duration=original_duration,
        edited_duration=edited_duration,
        has_narration=bool(narration_text),
        has_new_storyline=bool(narration_text),
        visual_changes=config.visual_changes(),
        audio_replaced=True,  # We always remove original audio
        bgm_source="tts_only" if narration_text else "none",
    )

    # Save manifest
    import json
    (output_dir / "edit_manifest.json").write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2)
    )

    return manifest
```

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add editor module with FFmpeg transforms and narration stubs"
```

---

## Task 7: Translator Module

**Files:**
- Create: `src/autoshorts/translator/__init__.py`
- Create: `src/autoshorts/translator/tts.py`
- Create: `src/autoshorts/translator/subtitle.py`
- Create: `src/autoshorts/translator/runner.py`
- Test: `tests/translator/__init__.py`
- Test: `tests/translator/test_subtitle.py`

**Step 1: Write the failing test**

```python
# tests/translator/test_subtitle.py
from autoshorts.translator.subtitle import generate_srt, SrtEntry


def test_generate_srt():
    entries = [
        SrtEntry(index=1, start="00:00:00,000", end="00:00:03,000", text="Hello world"),
        SrtEntry(index=2, start="00:00:03,000", end="00:00:06,000", text="This is a test"),
    ]
    srt = generate_srt(entries)
    assert "1\n00:00:00,000 --> 00:00:03,000\nHello world" in srt
    assert "2\n00:00:03,000 --> 00:00:06,000\nThis is a test" in srt


def test_srt_entry_from_seconds():
    entry = SrtEntry.from_seconds(1, 0.0, 3.5, "Test text")
    assert entry.start == "00:00:00,000"
    assert entry.end == "00:00:03,500"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/translator/test_subtitle.py -v`
Expected: FAIL

**Step 3: Implement subtitle module**

```python
# src/autoshorts/translator/__init__.py
"""Translator module — multi-language subtitle and TTS."""
```

```python
# src/autoshorts/translator/subtitle.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SrtEntry:
    index: int
    start: str
    end: str
    text: str

    @classmethod
    def from_seconds(cls, index: int, start_sec: float, end_sec: float, text: str) -> SrtEntry:
        return cls(
            index=index,
            start=_format_timestamp(start_sec),
            end=_format_timestamp(end_sec),
            text=text,
        )


def _format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(entries: list[SrtEntry]) -> str:
    blocks = []
    for entry in entries:
        blocks.append(f"{entry.index}\n{entry.start} --> {entry.end}\n{entry.text}")
    return "\n\n".join(blocks) + "\n"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/translator/test_subtitle.py -v`
Expected: PASS

**Step 5: Create TTS module**

```python
# src/autoshorts/translator/tts.py
from __future__ import annotations

import asyncio
from pathlib import Path

# Language → edge-tts voice mapping
VOICE_MAP = {
    "en": "en-US-AriaNeural",
    "ko": "ko-KR-SunHiNeural",
    "ja": "ja-JP-NanamiNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "pt": "pt-BR-FranciscaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ar": "ar-SA-ZariyahNeural",
}


async def generate_tts(text: str, lang: str, output_path: Path) -> Path:
    """Generate TTS audio using edge-tts."""
    import edge_tts

    voice = VOICE_MAP.get(lang, "en-US-AriaNeural")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    return output_path
```

**Step 6: Create translator runner**

```python
# src/autoshorts/translator/runner.py
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from autoshorts.translator.tts import generate_tts
from autoshorts.translator.subtitle import SrtEntry, generate_srt


async def translate_and_localize(
    input_dir: Path,
    languages: list[str],
    storyline: str,
) -> dict[str, Path]:
    """Translate storyline to multiple languages, generate TTS and subtitles."""
    results: dict[str, Path] = {}

    for lang in languages:
        lang_dir = input_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        # TODO: Use Claude subscription to translate storyline
        # For now, placeholder
        translated_text = storyline  # Will be replaced with actual translation

        # Generate TTS
        tts_path = lang_dir / "narration.mp3"
        await generate_tts(translated_text, lang, tts_path)

        # Generate SRT (simplified: one entry for now)
        entries = [SrtEntry.from_seconds(1, 0.0, 5.0, translated_text)]
        srt_content = generate_srt(entries)
        srt_path = lang_dir / "subtitles.srt"
        srt_path.write_text(srt_content, encoding="utf-8")

        # Save localization metadata
        meta = {
            "language": lang,
            "tts_path": str(tts_path),
            "srt_path": str(srt_path),
            "translated_text": translated_text,
        }
        (lang_dir / "localize_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)
        )

        results[lang] = lang_dir

    return results
```

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add translator module with edge-tts and SRT generation"
```

---

## Task 8: Uploader Module

**Files:**
- Create: `src/autoshorts/uploader/__init__.py`
- Create: `src/autoshorts/uploader/base.py`
- Create: `src/autoshorts/uploader/youtube.py`
- Create: `src/autoshorts/uploader/tiktok.py`
- Create: `src/autoshorts/uploader/instagram.py`
- Create: `src/autoshorts/uploader/facebook.py`
- Create: `src/autoshorts/uploader/threads.py`
- Create: `src/autoshorts/uploader/snapchat.py`
- Create: `src/autoshorts/uploader/scheduler.py`
- Create: `src/autoshorts/uploader/runner.py`
- Test: `tests/uploader/__init__.py`
- Test: `tests/uploader/test_scheduler.py`

**Step 1: Write the failing test for scheduler**

```python
# tests/uploader/test_scheduler.py
from datetime import datetime, timezone
from autoshorts.uploader.scheduler import get_optimal_upload_time, TIMEZONE_MAP


def test_us_primetime():
    time = get_optimal_upload_time("en", "US")
    # US primetime is 18:00-21:00 EST
    assert 17 <= time.hour <= 21


def test_japan_primetime():
    time = get_optimal_upload_time("ja", "JP")
    # Japan primetime is 19:00-22:00 JST
    assert 18 <= time.hour <= 22


def test_timezone_map_has_all_languages():
    required = ["en", "ko", "ja", "de", "fr", "es", "pt", "hi", "ar"]
    for lang in required:
        assert lang in TIMEZONE_MAP
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/uploader/test_scheduler.py -v`
Expected: FAIL

**Step 3: Implement scheduler**

```python
# src/autoshorts/uploader/__init__.py
"""Uploader module — multi-platform video publishing."""
```

```python
# src/autoshorts/uploader/scheduler.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone, time

TIMEZONE_MAP = {
    "en": {"tz_offset": -5, "country": "US", "primetime_start": 18, "primetime_end": 21},
    "ko": {"tz_offset": 9, "country": "KR", "primetime_start": 19, "primetime_end": 22},
    "ja": {"tz_offset": 9, "country": "JP", "primetime_start": 19, "primetime_end": 22},
    "de": {"tz_offset": 1, "country": "DE", "primetime_start": 18, "primetime_end": 21},
    "fr": {"tz_offset": 1, "country": "FR", "primetime_start": 18, "primetime_end": 21},
    "es": {"tz_offset": 1, "country": "ES", "primetime_start": 19, "primetime_end": 22},
    "pt": {"tz_offset": -3, "country": "BR", "primetime_start": 19, "primetime_end": 22},
    "hi": {"tz_offset": 5, "country": "IN", "primetime_start": 19, "primetime_end": 22},
    "ar": {"tz_offset": 3, "country": "SA", "primetime_start": 20, "primetime_end": 23},
}


def get_optimal_upload_time(lang: str, country: str | None = None) -> datetime:
    """Calculate the next optimal upload time for a given language/market."""
    info = TIMEZONE_MAP.get(lang, TIMEZONE_MAP["en"])

    tz = timezone(timedelta(hours=info["tz_offset"]))
    now = datetime.now(tz)

    # Target: middle of primetime
    target_hour = (info["primetime_start"] + info["primetime_end"]) // 2

    target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

    # If past primetime today, schedule for tomorrow
    if now.hour >= info["primetime_end"]:
        target += timedelta(days=1)

    return target
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/uploader/test_scheduler.py -v`
Expected: PASS

**Step 5: Create uploader base and platform stubs**

```python
# src/autoshorts/uploader/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime


@dataclass
class UploadResult:
    platform: str
    video_id: str
    success: bool
    url: str = ""
    error: str = ""
    uploaded_at: str = ""


class PlatformUploader(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        ...

    @abstractmethod
    async def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: datetime | None = None,
    ) -> UploadResult:
        ...
```

```python
# src/autoshorts/uploader/youtube.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime

from autoshorts.uploader.base import PlatformUploader, UploadResult


class YouTubeUploader(PlatformUploader):
    @property
    def platform_name(self) -> str:
        return "youtube"

    async def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: datetime | None = None,
    ) -> UploadResult:
        # TODO: Implement with YouTube Data API v3
        # 1. Authenticate with OAuth2
        # 2. Upload video as Shorts (#Shorts in title)
        # 3. Set metadata (title, description, tags, category)
        # 4. Set schedule if provided
        raise NotImplementedError("YouTube uploader not yet implemented")
```

```python
# src/autoshorts/uploader/tiktok.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from autoshorts.uploader.base import PlatformUploader, UploadResult


class TikTokUploader(PlatformUploader):
    @property
    def platform_name(self) -> str:
        return "tiktok"

    async def upload(self, video_path: Path, title: str, description: str,
                     tags: list[str], schedule_time: datetime | None = None) -> UploadResult:
        raise NotImplementedError("TikTok uploader not yet implemented")
```

```python
# src/autoshorts/uploader/instagram.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from autoshorts.uploader.base import PlatformUploader, UploadResult


class InstagramUploader(PlatformUploader):
    @property
    def platform_name(self) -> str:
        return "instagram"

    async def upload(self, video_path: Path, title: str, description: str,
                     tags: list[str], schedule_time: datetime | None = None) -> UploadResult:
        raise NotImplementedError("Instagram uploader not yet implemented")
```

```python
# src/autoshorts/uploader/facebook.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from autoshorts.uploader.base import PlatformUploader, UploadResult


class FacebookUploader(PlatformUploader):
    @property
    def platform_name(self) -> str:
        return "facebook"

    async def upload(self, video_path: Path, title: str, description: str,
                     tags: list[str], schedule_time: datetime | None = None) -> UploadResult:
        raise NotImplementedError("Facebook uploader not yet implemented")
```

```python
# src/autoshorts/uploader/threads.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from autoshorts.uploader.base import PlatformUploader, UploadResult


class ThreadsUploader(PlatformUploader):
    @property
    def platform_name(self) -> str:
        return "threads"

    async def upload(self, video_path: Path, title: str, description: str,
                     tags: list[str], schedule_time: datetime | None = None) -> UploadResult:
        raise NotImplementedError("Threads uploader not yet implemented")
```

```python
# src/autoshorts/uploader/snapchat.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from autoshorts.uploader.base import PlatformUploader, UploadResult


class SnapchatUploader(PlatformUploader):
    @property
    def platform_name(self) -> str:
        return "snapchat"

    async def upload(self, video_path: Path, title: str, description: str,
                     tags: list[str], schedule_time: datetime | None = None) -> UploadResult:
        raise NotImplementedError("Snapchat uploader not yet implemented")
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add uploader module with scheduler and 6 platform adapters"
```

---

## Task 9: Pipeline Orchestration

**Files:**
- Create: `src/autoshorts/pipeline/__init__.py`
- Create: `src/autoshorts/pipeline/state.py`
- Create: `src/autoshorts/pipeline/runner.py`
- Test: `tests/pipeline/__init__.py`
- Test: `tests/pipeline/test_state.py`

**Step 1: Write the failing test**

```python
# tests/pipeline/test_state.py
from pathlib import Path
from autoshorts.pipeline.state import PipelineState, StageStatus


def test_initial_state():
    state = PipelineState.new("run_001")
    assert state.run_id == "run_001"
    assert state.current_stage == "collect"
    assert all(s == StageStatus.PENDING for s in state.stages.values())


def test_advance_stage():
    state = PipelineState.new("run_001")
    state.advance("collect", StageStatus.COMPLETED)
    assert state.stages["collect"] == StageStatus.COMPLETED
    assert state.current_stage == "validate_source"


def test_save_and_load(tmp_path):
    state = PipelineState.new("run_002")
    state.advance("collect", StageStatus.COMPLETED)
    path = tmp_path / "state.json"
    state.save(path)

    loaded = PipelineState.load(path)
    assert loaded.run_id == "run_002"
    assert loaded.stages["collect"] == StageStatus.COMPLETED
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipeline/test_state.py -v`
Expected: FAIL

**Step 3: Implement pipeline state**

```python
# src/autoshorts/pipeline/__init__.py
"""Pipeline orchestration module."""
```

```python
# src/autoshorts/pipeline/state.py
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime

STAGE_ORDER = [
    "collect",
    "validate_source",
    "edit",
    "validate_transform",
    "translate",
    "validate_final",
    "upload",
]


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineState:
    run_id: str
    current_stage: str
    stages: dict[str, StageStatus]
    started_at: str = ""
    updated_at: str = ""
    stats: dict = field(default_factory=dict)

    @classmethod
    def new(cls, run_id: str) -> PipelineState:
        now = datetime.now().isoformat()
        return cls(
            run_id=run_id,
            current_stage=STAGE_ORDER[0],
            stages={s: StageStatus.PENDING for s in STAGE_ORDER},
            started_at=now,
            updated_at=now,
        )

    def advance(self, stage: str, status: StageStatus) -> None:
        self.stages[stage] = status
        self.updated_at = datetime.now().isoformat()

        if status == StageStatus.COMPLETED:
            idx = STAGE_ORDER.index(stage)
            if idx + 1 < len(STAGE_ORDER):
                self.current_stage = STAGE_ORDER[idx + 1]

    def save(self, path: Path) -> None:
        data = asdict(self)
        data["stages"] = {k: v.value for k, v in self.stages.items()}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> PipelineState:
        data = json.loads(path.read_text())
        data["stages"] = {k: StageStatus(v) for k, v in data["stages"].items()}
        return cls(**data)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipeline/test_state.py -v`
Expected: PASS

**Step 5: Create pipeline runner**

```python
# src/autoshorts/pipeline/runner.py
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from autoshorts.pipeline.state import PipelineState, StageStatus, STAGE_ORDER
from autoshorts.common.storage import DIRS, ensure_dirs


STATE_FILE = Path("data/pipeline_state.json")


def run_pipeline() -> PipelineState:
    """Execute the full pipeline once."""
    ensure_dirs()

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    state = PipelineState.new(run_id)
    state.save(STATE_FILE)

    for stage in STAGE_ORDER:
        state.advance(stage, StageStatus.IN_PROGRESS)
        state.save(STATE_FILE)

        try:
            _execute_stage(stage, state)
            state.advance(stage, StageStatus.COMPLETED)
        except Exception as e:
            state.advance(stage, StageStatus.FAILED)
            state.stats[f"{stage}_error"] = str(e)
            state.save(STATE_FILE)
            raise

        state.save(STATE_FILE)

    return state


def _execute_stage(stage: str, state: PipelineState) -> None:
    """Execute a single pipeline stage."""
    # TODO: Wire each stage to its module runner
    # For now, each stage is a placeholder
    if stage == "collect":
        pass  # Will call collector.runner.collect()
    elif stage == "validate_source":
        pass  # Will call validator.runner.validate_source()
    elif stage == "edit":
        pass  # Will call editor.runner.edit_video()
    elif stage == "validate_transform":
        pass  # Will call validator Stage 2
    elif stage == "translate":
        pass  # Will call translator.runner
    elif stage == "validate_final":
        pass  # Will call validator Stage 3
    elif stage == "upload":
        pass  # Will call uploader.runner


def get_status() -> dict:
    """Get current pipeline status (for heartbeat)."""
    if not STATE_FILE.exists():
        return {"status": "idle", "message": "No pipeline run found"}

    state = PipelineState.load(STATE_FILE)
    return {
        "status": "running" if any(
            s == StageStatus.IN_PROGRESS for s in state.stages.values()
        ) else "idle",
        "run_id": state.run_id,
        "current_stage": state.current_stage,
        "stages": {k: v.value for k, v in state.stages.items()},
        "updated_at": state.updated_at,
    }
```

**Step 6: Wire pipeline CLI commands in cli.py**

```python
@pipeline.command()
def run():
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
    import json
    from autoshorts.pipeline.runner import get_status
    click.echo(json.dumps(get_status(), indent=2, ensure_ascii=False))


@pipeline.command()
def heartbeat():
    """Heartbeat check for OpenClaw monitoring."""
    from autoshorts.pipeline.runner import get_status
    status_data = get_status()
    click.echo(json.dumps(status_data))
```

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add pipeline orchestration with state management and CLI commands"
```

---

## Task 10: Config Files

**Files:**
- Create: `config/platforms.yaml`
- Create: `config/languages.yaml`
- Create: `config/schedule.yaml`

**Step 1: Create platform config**

```yaml
# config/platforms.yaml
collector:
  douyin:
    enabled: true
    base_url: "https://www.douyin.com"
    max_per_session: 50
  kuaishou:
    enabled: true
    base_url: "https://www.kuaishou.com"
    max_per_session: 50
  bilibili:
    enabled: true
    base_url: "https://www.bilibili.com"
    max_per_session: 50
  xiaohongshu:
    enabled: true
    base_url: "https://www.xiaohongshu.com"
    max_per_session: 50

uploader:
  youtube:
    enabled: true
    daily_limit_per_channel: 2
    api: "data_api_v3"
  tiktok:
    enabled: true
    daily_limit_per_channel: 2
    api: "tiktok_api"
  instagram:
    enabled: true
    daily_limit_per_channel: 2
    api: "graph_api"
  facebook:
    enabled: true
    daily_limit_per_channel: 2
    api: "graph_api"
  threads:
    enabled: true
    daily_limit_per_channel: 2
    api: "threads_api"
  snapchat:
    enabled: true
    daily_limit_per_channel: 1
    api: "snapchat_api"
```

**Step 2: Create languages config**

```yaml
# config/languages.yaml
languages:
  # Tier 1 - High CPM ($15-40)
  en:
    name: "English"
    tier: 1
    targets: ["US", "UK", "CA", "AU"]
    tts_voice: "en-US-AriaNeural"
    channel_suffix: "EN"
    content_style: "funny/surprising"
  de:
    name: "German"
    tier: 1
    targets: ["DE", "AT", "CH"]
    tts_voice: "de-DE-KatjaNeural"
    channel_suffix: "DE"
    content_style: "informative"
  ja:
    name: "Japanese"
    tier: 1
    targets: ["JP"]
    tts_voice: "ja-JP-NanamiNeural"
    channel_suffix: "JP"
    content_style: "kawaii/cute"

  # Tier 2 - Medium CPM ($5-15)
  ko:
    name: "Korean"
    tier: 2
    targets: ["KR"]
    tts_voice: "ko-KR-SunHiNeural"
    channel_suffix: "KR"
    content_style: "cute/heartwarming"
  fr:
    name: "French"
    tier: 2
    targets: ["FR", "BE", "CA"]
    tts_voice: "fr-FR-DeniseNeural"
    channel_suffix: "FR"
    content_style: "charming"
  es:
    name: "Spanish"
    tier: 2
    targets: ["ES", "MX"]
    tts_voice: "es-ES-ElviraNeural"
    channel_suffix: "ES"
    content_style: "fun/energetic"
  pt:
    name: "Portuguese"
    tier: 2
    targets: ["BR"]
    tts_voice: "pt-BR-FranciscaNeural"
    channel_suffix: "BR"
    content_style: "fun/energetic"

  # Tier 3 - Volume (CPM $1-5)
  hi:
    name: "Hindi"
    tier: 3
    targets: ["IN"]
    tts_voice: "hi-IN-SwaraNeural"
    channel_suffix: "IN"
    content_style: "entertaining"
  ar:
    name: "Arabic"
    tier: 3
    targets: ["SA", "AE"]
    tts_voice: "ar-SA-ZariyahNeural"
    channel_suffix: "AR"
    content_style: "family-friendly"
```

**Step 3: Create schedule config**

```yaml
# config/schedule.yaml
# Upload schedule — primetime hours in local timezone
schedule:
  en: { tz: "America/New_York", hours: [18, 19, 20] }
  ko: { tz: "Asia/Seoul", hours: [19, 20, 21] }
  ja: { tz: "Asia/Tokyo", hours: [19, 20, 21] }
  de: { tz: "Europe/Berlin", hours: [18, 19, 20] }
  fr: { tz: "Europe/Paris", hours: [18, 19, 20] }
  es: { tz: "Europe/Madrid", hours: [19, 20, 21] }
  pt: { tz: "America/Sao_Paulo", hours: [19, 20, 21] }
  hi: { tz: "Asia/Kolkata", hours: [19, 20, 21] }
  ar: { tz: "Asia/Riyadh", hours: [20, 21, 22] }

pipeline:
  # How many times to run collector per day
  collect_runs_per_day: 3
  # Max videos to collect per run
  collect_limit: 200
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add platform, language, and schedule config files"
```

---

## Task 11: OpenClaw Guide & Skills

**Files:**
- Create: `docs/openclaw-guide/README.md`
- Create: `docs/openclaw-guide/commands.md`
- Create: `docs/openclaw-guide/hooks.md`
- Create: `docs/openclaw-guide/troubleshooting.md`
- Create: `docs/openclaw-guide/daily-operations.md`
- Create: `skills/autoshorts-operator.md`
- Create: `skills/autoshorts-monitor.md`
- Create: `skills/autoshorts-troubleshoot.md`

**Step 1: Create OpenClaw quickstart README**

```markdown
# AutoShorts — OpenClaw 운영 가이드

이 문서만 읽으면 AutoShorts 파이프라인을 운영할 수 있습니다.

## 시스템 개요

AutoShorts는 중국 SNS에서 동물 영상을 수집하고, 저작권 검증 후, 편집/번역하여 6개 플랫폼에 자동 업로드하는 파이프라인입니다.

## 빠른 시작

### 1. 전체 파이프라인 1회 실행
```bash
autoshorts pipeline run
```

### 2. 현재 상태 확인
```bash
autoshorts pipeline status
```

### 3. 하트비트 체크 (크론잡에 등록)
```bash
autoshorts pipeline heartbeat
```

## 핵심 커맨드

| 명령 | 설명 |
|------|------|
| `autoshorts pipeline run` | 전체 파이프라인 1회 실행 |
| `autoshorts pipeline status` | 현재 상태 확인 |
| `autoshorts pipeline heartbeat` | 하트비트 (JSON 출력) |
| `autoshorts collector run --platform all --limit 200` | 영상 수집 |
| `autoshorts validate source --input data/raw/<date>/` | Stage 1 검증 |
| `autoshorts validate final --input data/edited/<date>/` | Stage 2+3 검증 |
| `autoshorts validate report` | 검증 리포트 확인 |
| `autoshorts upload status` | 업로드 상태 확인 |

## 훅 설정

`hooks/` 디렉토리의 스크립트들을 Claude Code 훅으로 등록하세요:

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

## 일일 루틴

1. **아침:** `autoshorts pipeline run` 실행
2. **수시:** `autoshorts pipeline heartbeat` 로 상태 확인
3. **저녁:** `autoshorts validate report` 로 오늘의 검증 결과 리뷰
4. **검토 필요 영상:** Stage 3 점수 11-30 영상은 직접 판단

## 주의사항

- 저작권 검증 Stage 3에서 점수 11-30 사이 영상은 당신이 직접 판단해야 합니다
- `data/strategy_report.json`을 확인하여 수집 전략이 적절한지 모니터링하세요
- 채널당 하루 1-2개 이상 업로드하지 마세요

자세한 내용은 같은 디렉토리의 다른 문서를 참조하세요:
- [commands.md](commands.md) — 전체 CLI 레퍼런스
- [hooks.md](hooks.md) — 훅 설정 상세
- [troubleshooting.md](troubleshooting.md) — 문제 해결
- [daily-operations.md](daily-operations.md) — 일일 운영 상세
```

**Step 2: Create commands reference**

```markdown
# CLI 커맨드 레퍼런스

## collector

### `autoshorts collector run`

영상 수집을 실행합니다.

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--platform` | choice | `all` | douyin, kuaishou, bilibili, xiaohongshu, all |
| `--limit` | int | `50` | 수집할 최대 영상 수 |

출력: 수집된 영상 수
데이터: `data/raw/{date}/{platform}_{id}/meta.json`

### `autoshorts collector status`

수집 현황을 날짜별로 보여줍니다.

## validate

### `autoshorts validate source --input <path>`

Stage 1 소스 검증을 실행합니다. 편집 전 원본 영상의 저작권 안전성을 확인합니다.

| 옵션 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `--input` | path | Yes | 검증할 영상 디렉토리 |

출력: 통과/거부 수, 높은 폐기율 경고
데이터: 각 영상 디렉토리에 `validation_source.json` 생성

### `autoshorts validate final --input <path>`

Stage 2 (변환 충분성) + Stage 3 (최종 AI 판정) 검증을 실행합니다.

### `autoshorts validate report`

`data/strategy_report.json`의 내용을 보여줍니다. 폐기율, 주요 폐기 사유, 전략 조정 내역을 확인할 수 있습니다.

## edit

### `autoshorts edit --input <path>`

영상을 편집합니다. FFmpeg로 시각 변형 + AI 나레이션 생성.

### `autoshorts edit --retry <id>`

Stage 2 검증 실패한 영상을 더 강하게 재편집합니다 (최대 3회).

## translate

### `autoshorts translate --input <path> --langs <codes>`

편집된 영상을 다중 언어로 번역합니다.

| 옵션 | 타입 | 설명 |
|------|------|------|
| `--input` | path | 편집된 영상 디렉토리 |
| `--langs` | string | 쉼표 구분 언어 코드 (en,ja,de,ko,fr,es,pt) |

## upload

### `autoshorts upload --input <path> --platforms <names>`

영상을 지정된 플랫폼에 업로드합니다.

| 옵션 | 타입 | 설명 |
|------|------|------|
| `--input` | path | 최종 영상 디렉토리 |
| `--platforms` | string | 쉼표 구분 플랫폼 (youtube,tiktok,instagram,facebook,threads,snapchat) |

### `autoshorts upload status`

업로드 현황을 보여줍니다.

### `autoshorts upload schedule`

언어별 최적 업로드 시간을 보여줍니다.

## pipeline

### `autoshorts pipeline run`

전체 파이프라인을 1회 실행합니다: 수집 → 검증 → 편집 → 검증 → 번역 → 검증 → 업로드

### `autoshorts pipeline status`

현재 파이프라인 상태를 JSON으로 출력합니다.

### `autoshorts pipeline heartbeat`

하트비트 체크용. 현재 상태를 한 줄 JSON으로 출력합니다.
OpenClaw 크론잡에 등록하여 주기적으로 확인하세요.
```

**Step 3: Create hooks guide**

```markdown
# 훅 설정 가이드

## 훅 목록

| 훅 | 트리거 | 역할 |
|----|--------|------|
| `on_collect_complete` | 수집 완료 | Stage 1 검증 시작 |
| `on_validate_pass` | 검증 통과 | 다음 단계 시작 (편집 또는 업로드) |
| `on_validate_fail` | 검증 실패 | 폐기 로그 기록, 전략 리포트 업데이트 |
| `on_edit_complete` | 편집 완료 | Stage 2 검증 시작 |
| `on_upload_complete` | 업로드 성공 | 결과 리포트 생성 |
| `on_upload_fail` | 업로드 실패 | 재시도 또는 에러 보고 |
| `heartbeat` | 주기적 (5분) | 파이프라인 상태 체크 |
| `daily_report` | 매일 23:00 | 일일 운영 리포트 생성 |

## 훅 스크립트 작성법

각 훅 스크립트는 `hooks/` 디렉토리에 위치합니다.

### on_collect_complete.sh

```bash
#!/bin/bash
# 수집 완료 → Stage 1 검증 시작
DATE=$(date +%Y-%m-%d)
autoshorts validate source --input "data/raw/$DATE/"
```

### on_validate_pass.sh

```bash
#!/bin/bash
# 검증 통과 → 다음 단계 진행
STAGE=$1  # source, transform, final
VIDEO_ID=$2

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

### on_validate_fail.sh

```bash
#!/bin/bash
# 검증 실패 → 로그 + 전략 리포트
STAGE=$1
VIDEO_ID=$2
REASON=$3

echo "[$(date)] REJECTED: $VIDEO_ID (stage=$STAGE, reason=$REASON)" >> data/rejection.log

# Stage 2 실패 시 재편집 시도 (최대 3회)
if [ "$STAGE" = "transform" ]; then
  RETRY_COUNT=$(cat "data/edited/$VIDEO_ID/retry_count" 2>/dev/null || echo 0)
  if [ "$RETRY_COUNT" -lt 3 ]; then
    echo $((RETRY_COUNT + 1)) > "data/edited/$VIDEO_ID/retry_count"
    autoshorts edit --retry "$VIDEO_ID"
  fi
fi
```

### heartbeat (크론잡)

```bash
# crontab -e에 추가
*/5 * * * * autoshorts pipeline heartbeat >> /tmp/autoshorts_heartbeat.log
```

### daily_report (크론잡)

```bash
# 매일 23:00에 실행
0 23 * * * autoshorts validate report >> data/daily_reports/$(date +\%Y-\%m-\%d).json
```

## Claude Code 훅 설정

OpenClaw의 settings.json에 다음을 추가하세요:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "autoshorts collector run",
        "command": "bash hooks/on_collect_complete.sh"
      }
    ]
  }
}
```
```

**Step 4: Create troubleshooting guide**

```markdown
# 문제 해결 가이드

## 자주 발생하는 문제

### 1. 높은 폐기율 (>80%)

**증상:** `autoshorts validate report`에서 폐기율 80% 초과

**원인:** 수집 전략이 저작권 위험 영상을 많이 가져옴

**대응:**
```bash
# 현재 전략 리포트 확인
autoshorts validate report

# 주요 폐기 사유 확인 후 전략 자동 조정됨
# 다음 수집 사이클에서 반영
autoshorts collector run --platform all --limit 200
```

**수동 조정이 필요한 경우:**
- `data/strategy.json`을 직접 수정
- `prefer_cc_creators: true` — CC 라이선스 크리에이터 우선
- `prefer_recent: true` — 최신 영상 우선
- `prefer_outdoor: true` — 야외 촬영 영상 우선

### 2. 편집 후 변환 검증 실패

**증상:** Stage 2에서 "insufficient_transformation" 반복

**대응:**
```bash
# 자동 재편집 (더 강한 변환 적용)
autoshorts edit --retry <video_id>
```
최대 3회 재시도. 3회 모두 실패하면 해당 영상 폐기.

### 3. 업로드 실패

**증상:** `autoshorts upload status`에서 에러 표시

**일반적 원인 및 대응:**
- **API 할당량 초과** → 내일까지 대기. 채널당 일일 제한 확인
- **인증 만료** → API 토큰 갱신 (`config/secrets.yaml`)
- **영상 규격 불일치** → FFmpeg 출력 설정 확인

### 4. 파이프라인 중단

**증상:** `autoshorts pipeline status`에서 특정 stage가 `failed`

**대응:**
```bash
# 상태 확인
autoshorts pipeline status

# 실패한 단계의 에러 로그 확인
# data/pipeline_state.json에서 에러 메시지 확인

# 해당 단계만 재실행하거나 전체 재실행
autoshorts pipeline run
```

### 5. Playwright 크롤링 실패

**증상:** 수집 0건, 에러 로그에 "timeout" 또는 "navigation failed"

**대응:**
- 해당 플랫폼 접속 가능 여부 확인
- Playwright 브라우저 업데이트: `playwright install`
- 특정 플랫폼만 비활성화: `config/platforms.yaml`에서 `enabled: false`
```

**Step 5: Create daily operations guide**

```markdown
# 일일 운영 가이드

## 아침 루틴 (1회)

```bash
# 1. 파이프라인 실행
autoshorts pipeline run

# 2. 어제 리포트 확인
autoshorts validate report
```

## 수시 모니터링

```bash
# 하트비트 확인 (크론잡으로 자동화 권장)
autoshorts pipeline heartbeat
```

**정상 응답 예시:**
```json
{
  "status": "idle",
  "run_id": "run_20260325_090000",
  "current_stage": "upload",
  "stages": {
    "collect": "completed",
    "validate_source": "completed",
    "edit": "completed",
    "validate_transform": "completed",
    "translate": "completed",
    "validate_final": "completed",
    "upload": "completed"
  }
}
```

## Stage 3 수동 판단

점수 11-30 영상이 있으면 직접 확인이 필요합니다:

```bash
# 수동 검토 대상 확인
ls data/final/*/validation_final.json | xargs grep '"action": "openclaw_review"'
```

판단 기준:
- 원본과 충분히 다른가?
- 나레이션/스토리가 새로운가?
- 브랜드/로고가 확실히 없는가?

확인 후:
- **통과:** 해당 영상의 validation_final.json에서 `action`을 `"auto_upload"`로 변경
- **거부:** `"auto_reject"`로 변경

## 주간 점검

- **수집 전략 리포트:** 폐기율 추이 확인, 50% 이상이면 전략 조정 필요
- **업로드 현황:** 채널별 업로드 수, 에러율 확인
- **API 할당량:** YouTube API 잔여 할당량 확인
```

**Step 6: Create OpenClaw skills**

```markdown
---
name: autoshorts-operator
description: AutoShorts 파이프라인 전체 운영 — 크론잡, 훅, 하트비트 설정 및 일일 운영
---

# AutoShorts Operator

당신은 AutoShorts 파이프라인의 운영자입니다.

## 핵심 역할

1. 매일 파이프라인을 실행하고 결과를 모니터링합니다
2. 저작권 검증에서 수동 판단이 필요한 영상을 검토합니다
3. 수집 전략이 적절한지 확인하고 필요시 조정합니다

## 운영 명령어

```bash
# 전체 파이프라인 실행
autoshorts pipeline run

# 상태 확인
autoshorts pipeline status
autoshorts pipeline heartbeat

# 검증 리포트
autoshorts validate report

# 업로드 상태
autoshorts upload status
```

## 크론잡 설정

```bash
# 하루 3회 파이프라인 실행 (09:00, 14:00, 19:00)
0 9,14,19 * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts pipeline run >> data/logs/pipeline.log 2>&1

# 5분마다 하트비트
*/5 * * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts pipeline heartbeat >> data/logs/heartbeat.log

# 매일 23:00 일일 리포트
0 23 * * * cd /Users/hwaa/Developer/AutoShorts && autoshorts validate report >> data/daily_reports/$(date +\%Y-\%m-\%d).json
```

## 판단이 필요한 상황

### Stage 3 수동 검토 (점수 11-30)

1. `data/final/*/validation_final.json`에서 `"action": "openclaw_review"` 확인
2. 해당 영상의 원본과 편집본을 비교
3. 저작권 위반 소지가 없다고 판단되면 → `"action": "auto_upload"` 변경
4. 위반 소지가 있으면 → `"action": "auto_reject"` 변경

### 높은 폐기율 대응

`autoshorts validate report`에서 폐기율이 80% 이상이면:
- `data/strategy_report.json`의 `top_reasons` 확인
- 시스템이 자동으로 전략을 조정하지만, 지속되면 수동 개입
- 참고: [troubleshooting.md](docs/openclaw-guide/troubleshooting.md)

## 참조

- 전체 커맨드 목록: `docs/openclaw-guide/commands.md`
- 훅 설정: `docs/openclaw-guide/hooks.md`
- 문제 해결: `docs/openclaw-guide/troubleshooting.md`
```

```markdown
---
name: autoshorts-monitor
description: AutoShorts 파이프라인 상태 모니터링 — 하트비트 체크, 에러 감지, 리포트 확인
---

# AutoShorts Monitor

파이프라인의 상태를 확인하고 이상 징후를 감지합니다.

## 체크 항목

### 1. 파이프라인 상태

```bash
autoshorts pipeline heartbeat
```

정상: `"status": "idle"` 또는 `"status": "running"`
비정상: stage 중 하나가 `"failed"`

### 2. 검증 리포트

```bash
autoshorts validate report
```

확인 포인트:
- `rejection_rate` < 0.5 → 정상
- `rejection_rate` 0.5-0.8 → 주의, 전략 조정 중
- `rejection_rate` > 0.8 → 경고, 수동 확인 필요

### 3. 업로드 상태

```bash
autoshorts upload status
```

확인 포인트:
- 모든 플랫폼 정상 업로드 여부
- 에러가 있으면 원인 확인

## 이상 감지 시 대응

1. 파이프라인 실패 → `docs/openclaw-guide/troubleshooting.md` 참조
2. 높은 폐기율 → 전략 자동 조정 확인, 지속 시 수동 개입
3. 업로드 에러 → API 인증/할당량 확인
```

```markdown
---
name: autoshorts-troubleshoot
description: AutoShorts 장애 대응 — 파이프라인 실패, 크롤링 에러, 업로드 실패 시 대응
---

# AutoShorts Troubleshoot

문제 발생 시 이 스킬을 사용하세요.

## 진단 순서

1. 현재 상태 확인:
```bash
autoshorts pipeline status
```

2. 에러 로그 확인:
```bash
cat data/pipeline_state.json | python -m json.tool
```

3. 문제 유형 판별:
- `collect` 실패 → 크롤링 문제
- `validate_*` 실패 → 검증 로직 에러
- `edit` 실패 → FFmpeg 문제
- `translate` 실패 → TTS 에러
- `upload` 실패 → API 에러

## 유형별 대응

### 크롤링 실패
```bash
# Playwright 브라우저 업데이트
playwright install

# 특정 플랫폼만 테스트
autoshorts collector run --platform douyin --limit 5
```

### FFmpeg 에러
```bash
# FFmpeg 설치 확인
ffmpeg -version

# 특정 영상 재편집
autoshorts edit --retry <video_id>
```

### API 에러
- YouTube API 할당량: Google Cloud Console에서 확인
- 인증 토큰 갱신: `config/secrets.yaml` 업데이트

### 전체 재시작
```bash
# 파이프라인 상태 초기화 후 재실행
rm data/pipeline_state.json
autoshorts pipeline run
```

상세 가이드: `docs/openclaw-guide/troubleshooting.md`
```

**Step 7: Create hook scripts**

```bash
# hooks/on_collect_complete.sh
#!/bin/bash
DATE=$(date +%Y-%m-%d)
echo "[$(date)] Collection complete. Starting source validation..." >> data/logs/hooks.log
autoshorts validate source --input "data/raw/$DATE/"
```

```bash
# hooks/on_validate_pass.sh
#!/bin/bash
STAGE=$1
VIDEO_ID=$2
echo "[$(date)] Validation PASSED: stage=$STAGE video=$VIDEO_ID" >> data/logs/hooks.log
```

```bash
# hooks/on_validate_fail.sh
#!/bin/bash
STAGE=$1
VIDEO_ID=$2
REASON=$3
echo "[$(date)] Validation FAILED: stage=$STAGE video=$VIDEO_ID reason=$REASON" >> data/logs/hooks.log
```

```bash
# hooks/on_upload_complete.sh
#!/bin/bash
VIDEO_ID=$1
PLATFORM=$2
echo "[$(date)] Upload SUCCESS: video=$VIDEO_ID platform=$PLATFORM" >> data/logs/hooks.log
```

```bash
# hooks/on_upload_fail.sh
#!/bin/bash
VIDEO_ID=$1
PLATFORM=$2
ERROR=$3
echo "[$(date)] Upload FAILED: video=$VIDEO_ID platform=$PLATFORM error=$ERROR" >> data/logs/hooks.log
```

**Step 8: Commit**

```bash
chmod +x hooks/*.sh
git add -A
git commit -m "feat: add OpenClaw guide, skills, and hook scripts"
```

---

## Task 12: Architecture & Module Docs

**Files:**
- Create: `docs/architecture/overview.md`
- Create: `docs/architecture/data-flow.md`
- Create: `docs/architecture/copyright-policy.md`
- Create: `docs/modules/collector.md`
- Create: `docs/modules/validator.md`
- Create: `docs/modules/editor.md`
- Create: `docs/modules/translator.md`
- Create: `docs/modules/uploader.md`
- Create: `docs/setup/installation.md`
- Create: `docs/setup/api-keys.md`
- Create: `docs/setup/platform-accounts.md`

These are reference documentation files. Write them based on the implemented code, covering:
- Each module's purpose, API, and data flow
- Architecture diagrams in text
- Setup instructions for all external dependencies (FFmpeg, Playwright, API keys)
- Copyright policy explaining the 3-stage validation in detail

**Step 1: Write all docs (content mirrors the design document sections)**

**Step 2: Commit**

```bash
git add -A
git commit -m "docs: add architecture, module, and setup documentation"
```

---

## Task 13: Integration Tests

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test for pipeline state flow**

```python
# tests/test_integration.py
from pathlib import Path
from autoshorts.pipeline.state import PipelineState, StageStatus
from autoshorts.common.models import VideoMeta, VideoStatus
from autoshorts.validator.stage1 import SourceValidator
from autoshorts.validator.stage2 import TransformValidator, EditManifest
from autoshorts.validator.stage3 import FinalValidator, FinalCheckInput
from autoshorts.editor.transforms import EditConfig, build_ffmpeg_filters
from autoshorts.collector.strategy import SearchStrategy, StrategyEngine, RejectionStats


def test_full_validation_pipeline():
    """Test the 3-stage validation flow end-to-end (without actual video files)."""

    # Stage 1: Source validation
    meta = VideoMeta(
        id="integration_test_001",
        platform="douyin",
        source_url="https://example.com",
        title="小猫在花园里玩耍",
        author="catgarden",
        duration_seconds=25,
        tags=["cat", "garden", "outdoor"],
        license_info="cc-by",
    )
    source_validator = SourceValidator()
    s1_result = source_validator.check_metadata(meta)
    assert s1_result.passed, f"Stage 1 should pass: {s1_result.reasons}"

    # Stage 2: Transform validation
    edit_config = EditConfig.random_strong()
    manifest = EditManifest(
        video_id=meta.id,
        original_duration=25.0,
        edited_duration=23.0,
        has_narration=True,
        has_new_storyline=True,
        visual_changes=edit_config.visual_changes() + ["speed_change", "flip", "crop", "color_grade"],
        audio_replaced=True,
        bgm_source="royalty_free",
    )
    transform_validator = TransformValidator()
    s2_result = transform_validator.check(manifest)
    assert s2_result.passed, f"Stage 2 should pass: {s2_result.reasons}"

    # Stage 3: Final validation
    final_input = FinalCheckInput(
        video_id=meta.id,
        risk_score=5,
        risk_reasons=[],
    )
    final_validator = FinalValidator()
    s3_result = final_validator.check(final_input)
    assert s3_result.passed
    assert s3_result.details["action"] == "auto_upload"


def test_strategy_adjustment_cycle(tmp_path):
    """Test that high rejection rates trigger strategy adjustments."""
    engine = StrategyEngine(data_dir=tmp_path)
    strategy = SearchStrategy.default()

    # Simulate high rejection
    stats = RejectionStats(
        total_collected=100,
        total_rejected=85,
        reasons={"already_on_youtube": 50, "brand_detected": 20, "license_unclear": 15},
    )

    adjusted = engine.adjust(strategy, stats)
    assert adjusted.prefer_unpopular is True  # Shifted away from popular videos
    assert adjusted.prefer_cc_creators is True  # Shifted to CC creators

    # Verify report was saved
    report_path = tmp_path / "strategy_report.json"
    assert report_path.exists()
```

**Step 2: Run tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add -A
git commit -m "test: add integration tests for validation pipeline and strategy adjustment"
```

---

## Summary

| Task | Description | Est. Steps |
|------|-------------|-----------|
| 1 | Project scaffolding + CLI | 11 |
| 2 | Common data models | 7 |
| 3 | Collector + adapters + strategy | 12 |
| 4 | Validator Stage 1 | 6 |
| 5 | Validator Stage 2 + 3 | 11 |
| 6 | Editor module | 7 |
| 7 | Translator module | 7 |
| 8 | Uploader module | 6 |
| 9 | Pipeline orchestration | 7 |
| 10 | Config files | 4 |
| 11 | OpenClaw guide + skills + hooks | 8 |
| 12 | Architecture & module docs | 2 |
| 13 | Integration tests | 3 |

**Total: 13 tasks, ~91 steps**
