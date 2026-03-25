"""Instagram Reels uploader stub."""

from typing import Optional

from .base import PlatformUploader, UploadResult


class InstagramUploader(PlatformUploader):
    """Instagram Reels uploader (not yet implemented)."""

    @property
    def platform_name(self) -> str:
        return "instagram"

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        raise NotImplementedError("Instagram upload not yet implemented")
