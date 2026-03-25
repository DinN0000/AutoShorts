"""Facebook Reels uploader via Graph API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .base import PlatformUploader, UploadResult
from ._helpers import load_secrets, retry_upload

logger = logging.getLogger(__name__)


class FacebookUploader(PlatformUploader):
    """Upload Reels to Facebook via Graph API."""

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
        secrets = load_secrets("facebook")
        access_token = secrets.get("access_token")
        page_id = secrets.get("page_id")
        if not access_token or not page_id:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing facebook access_token or page_id in secrets",
            )

        async def _do_upload():
            return await self._upload_reel(
                access_token, page_id, video_path, title, description, tags, schedule_time,
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

    async def _upload_reel(
        self,
        access_token: str,
        page_id: str,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str],
    ) -> UploadResult:
        import aiohttp

        base_url = "https://graph.facebook.com/v19.0"
        tag_str = " ".join(f"#{t}" for t in tags)
        full_description = f"{title}\n\n{description}\n\n{tag_str}".strip()

        async with aiohttp.ClientSession() as session:
            # Step 1: Initialize upload
            init_url = f"{base_url}/{page_id}/video_reels"
            init_params = {
                "upload_phase": "start",
                "access_token": access_token,
            }
            async with session.post(init_url, params=init_params) as resp:
                data = await resp.json()
                if "video_id" not in data:
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"FB init error ({resp.status}): {error_msg}")
                video_id = data["video_id"]
                upload_url = data.get("upload_url", "")

            # Step 2: Upload binary
            with open(video_path, "rb") as f:
                video_data = f.read()

            if upload_url:
                target_url = upload_url
            else:
                target_url = f"{base_url}/{page_id}/video_reels"

            upload_headers = {
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_size": str(len(video_data)),
            }
            async with session.post(
                target_url, headers=upload_headers, data=video_data
            ) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"FB upload error ({resp.status}): {text}")

            # Step 3: Finish / publish
            finish_url = f"{base_url}/{page_id}/video_reels"
            finish_params: dict = {
                "upload_phase": "finish",
                "video_id": video_id,
                "title": title,
                "description": full_description,
                "access_token": access_token,
            }
            if schedule_time:
                finish_params["scheduled_publish_time"] = int(
                    datetime.fromisoformat(schedule_time).timestamp()
                )
                finish_params["published"] = "false"

            async with session.post(finish_url, params=finish_params) as resp:
                data = await resp.json()
                if not data.get("success", False):
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"FB finish error ({resp.status}): {error_msg}")

        return UploadResult(
            platform=self.platform_name,
            video_id=video_id,
            success=True,
            url=f"https://www.facebook.com/reel/{video_id}",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
