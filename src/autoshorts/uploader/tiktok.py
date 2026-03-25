"""TikTok uploader stub."""

from typing import Optional

from .base import PlatformUploader, UploadResult


class TikTokUploader(PlatformUploader):
    """TikTok uploader (not yet implemented)."""

    @property
    def platform_name(self) -> str:
        return "tiktok"

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        raise NotImplementedError("TikTok upload not yet implemented")
