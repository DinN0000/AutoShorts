"""Base adapter class for platform collectors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CollectResult:
    """Result from a video collection operation."""

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
    """Abstract base class for platform-specific adapters."""

    @property
    @abstractmethod
    def platform_name(self) -> str: ...

    @abstractmethod
    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]: ...

    @abstractmethod
    async def download(self, result: CollectResult, output_dir: Path) -> Path: ...
