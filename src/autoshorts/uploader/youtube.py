"""YouTube Shorts uploader stub."""

from typing import Optional

from .base import PlatformUploader, UploadResult


class YouTubeUploader(PlatformUploader):
    """YouTube Shorts uploader (not yet implemented)."""

    @property
    def platform_name(self) -> str:
        return "youtube"

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        raise NotImplementedError("YouTube upload not yet implemented")
