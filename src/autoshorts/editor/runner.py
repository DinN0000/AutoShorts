"""Editor runner — applies FFmpeg transforms to videos."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from .transforms import EditConfig, build_ffmpeg_filters


@dataclass
class EditRecord:
    """Record of an edit operation (distinct from validator's EditManifest)."""
    source_path: str
    output_path: str
    config: dict = field(default_factory=dict)
    filters_applied: str = ""
    edited_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))


async def edit_video(
    source_path: str,
    output_path: str,
    config: EditConfig | None = None,
) -> EditManifest:
    """Apply FFmpeg transforms to a video and return an EditManifest."""
    if config is None:
        config = EditConfig()

    filters = build_ffmpeg_filters(config)

    cmd = ["ffmpeg", "-y", "-i", source_path]
    if filters:
        cmd.extend(["-vf", filters])
    cmd.append(output_path)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (code {process.returncode}): {stderr.decode()}"
        )

    manifest = EditRecord(
        source_path=source_path,
        output_path=output_path,
        config=asdict(config),
        filters_applied=filters,
    )
    return manifest
