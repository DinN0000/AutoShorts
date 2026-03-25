"""Snapchat uploader via Snap Kit / Marketing API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .base import PlatformUploader, UploadResult
from ._helpers import load_secrets, retry_upload

logger = logging.getLogger(__name__)


class SnapchatUploader(PlatformUploader):
    """Upload video to Snapchat via Snap Marketing API (public story)."""

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
        secrets = load_secrets("snapchat")
        access_token = secrets.get("access_token")
        org_id = secrets.get("org_id")
        if not access_token or not org_id:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing snapchat access_token or org_id in secrets",
            )

        async def _do_upload():
            return await self._upload_video(
                access_token, org_id, video_path, title, description, tags,
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
        org_id: str,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
    ) -> UploadResult:
        import aiohttp
        import json

        base_url = "https://adsapi.snapchat.com/v1"

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Step 1: Create media
            create_url = f"{base_url}/organizations/{org_id}/media"
            media_body = {
                "media": [{
                    "name": title[:255],
                    "type": "VIDEO",
                }]
            }
            async with session.post(
                create_url, headers=headers, data=json.dumps(media_body)
            ) as resp:
                data = await resp.json()
                if resp.status not in (200, 201):
                    error_msg = str(data)
                    raise RuntimeError(f"Snap create error ({resp.status}): {error_msg}")
                media_list = data.get("media", [])
                if not media_list:
                    raise RuntimeError(f"Snap create: no media returned: {data}")
                media_obj = media_list[0].get("media", media_list[0])
                media_id = media_obj["id"]

            # Step 2: Upload video binary
            with open(video_path, "rb") as f:
                video_data = f.read()

            upload_url = f"{base_url}/media/{media_id}/upload"
            upload_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/mp4",
            }
            async with session.post(
                upload_url, headers=upload_headers, data=video_data
            ) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"Snap upload error ({resp.status}): {text}")

        return UploadResult(
            platform=self.platform_name,
            video_id=media_id,
            success=True,
            url=f"https://www.snapchat.com/spotlight/{media_id}",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
