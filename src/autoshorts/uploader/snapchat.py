"""Snapchat uploader stub."""

from typing import Optional

from .base import PlatformUploader, UploadResult


class SnapchatUploader(PlatformUploader):
    """Snapchat uploader (not yet implemented)."""

    @property
    def platform_name(self) -> str:
        return "snapchat"

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        raise NotImplementedError("Snapchat upload not yet implemented")
