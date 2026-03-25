"""Base classes for platform uploaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class UploadResult:
    """Result of an upload operation."""

    platform: str
    video_id: str
    success: bool
    url: str = ""
    error: str = ""
    uploaded_at: str = ""


class PlatformUploader(ABC):
    """Abstract base class for platform uploaders."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        ...

    @abstractmethod
    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        ...
