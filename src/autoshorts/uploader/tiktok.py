"""TikTok uploader via TikTok Content Posting API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .base import PlatformUploader, UploadResult
from ._helpers import load_secrets, retry_upload

logger = logging.getLogger(__name__)


class TikTokUploader(PlatformUploader):
    """Upload videos to TikTok via Content Posting API (direct post)."""

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
        secrets = load_secrets("tiktok")
        access_token = secrets.get("access_token")
        if not access_token:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing tiktok access_token in secrets",
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
        import os

        file_size = os.path.getsize(video_path)
        tag_str = " ".join(f"#{t}" for t in tags)
        caption = f"{title} {tag_str}".strip()

        # Step 1: Initialize upload
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        init_body = {
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
            },
        }
        if schedule_time:
            init_body["post_info"]["schedule_time"] = int(
                datetime.fromisoformat(schedule_time).timestamp()
            )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                init_url, headers=headers, data=json.dumps(init_body)
            ) as resp:
                data = await resp.json()
                if resp.status != 200 or data.get("error", {}).get("code") != "ok":
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"TikTok init error ({resp.status}): {error_msg}")

                publish_id = data["data"]["publish_id"]
                upload_url = data["data"]["upload_url"]

            # Step 2: Upload video binary
            with open(video_path, "rb") as f:
                video_data = f.read()

            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            }
            async with session.put(
                upload_url, headers=upload_headers, data=video_data
            ) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"TikTok upload error ({resp.status}): {text}")

        return UploadResult(
            platform=self.platform_name,
            video_id=publish_id,
            success=True,
            url=f"https://www.tiktok.com/@me/video/{publish_id}",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
