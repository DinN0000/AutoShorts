"""YouTube Shorts uploader via Google YouTube Data API v3."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from .base import PlatformUploader, UploadResult
from ._helpers import load_secrets, retry_upload

logger = logging.getLogger(__name__)


class YouTubeUploader(PlatformUploader):
    """Upload Shorts to YouTube via Data API v3 resumable upload."""

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
        secrets = load_secrets("youtube")
        access_token = secrets.get("access_token")
        if not access_token:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing youtube access_token in secrets",
            )

        async def _do_upload():
            return await self._upload_video(
                access_token, video_path, title, description, tags, schedule_time,
            )

        try:
            return await retry_upload(_do_upload, self.platform_name)
        except Exception as exc:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error=str(exc),
            )

    async def _upload_video(
        self,
        access_token: str,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str],
    ) -> UploadResult:
        import aiohttp
        import json

        privacy = "private" if schedule_time else "public"
        body: dict = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                "madeForKids": False,
            },
        }
        if schedule_time:
            body["status"]["publishAt"] = schedule_time
            body["status"]["privacyStatus"] = "private"

        metadata = json.dumps(body)
        url = (
            "https://www.googleapis.com/upload/youtube/v3/videos"
            "?uploadType=multipart&part=snippet,status"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        with open(video_path, "rb") as f:
            video_data = f.read()

        boundary = "autoshorts_boundary"
        multipart_body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{metadata}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: video/mp4\r\n"
            f"Content-Transfer-Encoding: binary\r\n\r\n"
        ).encode() + video_data + f"\r\n--{boundary}--".encode()

        headers["Content-Type"] = f"multipart/related; boundary={boundary}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=multipart_body) as resp:
                data = await resp.json()
                if resp.status not in (200, 201):
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"YouTube API error ({resp.status}): {error_msg}")

                video_id = data["id"]
                return UploadResult(
                    platform=self.platform_name,
                    video_id=video_id,
                    success=True,
                    url=f"https://youtube.com/shorts/{video_id}",
                    uploaded_at=datetime.now(timezone.utc).isoformat(),
                )
