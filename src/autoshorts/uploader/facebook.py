"""Facebook Reels uploader stub."""

from typing import Optional

from .base import PlatformUploader, UploadResult


class FacebookUploader(PlatformUploader):
    """Facebook Reels uploader (not yet implemented)."""

    @property
    def platform_name(self) -> str:
        return "facebook"

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        raise NotImplementedError("Facebook upload not yet implemented")
