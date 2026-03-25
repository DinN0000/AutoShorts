"""Threads uploader stub."""

from typing import Optional

from .base import PlatformUploader, UploadResult


class ThreadsUploader(PlatformUploader):
    """Threads uploader (not yet implemented)."""

    @property
    def platform_name(self) -> str:
        return "threads"

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        raise NotImplementedError("Threads upload not yet implemented")
