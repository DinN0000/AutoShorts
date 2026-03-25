"""Instagram Reels uploader via Instagram Graph API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from .base import PlatformUploader, UploadResult
from ._helpers import load_secrets, retry_upload

logger = logging.getLogger(__name__)

_STATUS_POLL_INTERVAL = 3
_STATUS_POLL_MAX = 30


class InstagramUploader(PlatformUploader):
    """Upload Reels to Instagram via Graph API (container-based flow)."""

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
        secrets = load_secrets("instagram")
        access_token = secrets.get("access_token")
        ig_user_id = secrets.get("user_id")
        if not access_token or not ig_user_id:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing instagram access_token or user_id in secrets",
            )
        video_url = secrets.get("video_host_url", "")
        if not video_url:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing instagram video_host_url in secrets (public URL required for Graph API)",
            )

        async def _do_upload():
            return await self._upload_reel(
                access_token, ig_user_id, video_url, video_path,
                title, description, tags, schedule_time,
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
        ig_user_id: str,
        video_url: str,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str],
    ) -> UploadResult:
        import aiohttp

        tag_str = " ".join(f"#{t}" for t in tags)
        caption = f"{title}\n\n{description}\n\n{tag_str}".strip()
        base_url = "https://graph.facebook.com/v19.0"

        async with aiohttp.ClientSession() as session:
            # Step 1: Create media container
            create_url = f"{base_url}/{ig_user_id}/media"
            params: dict = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": access_token,
            }
            async with session.post(create_url, params=params) as resp:
                data = await resp.json()
                if "id" not in data:
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"IG container error ({resp.status}): {error_msg}")
                container_id = data["id"]

            # Step 2: Poll until container is ready
            status_url = f"{base_url}/{container_id}"
            for _ in range(_STATUS_POLL_MAX):
                await asyncio.sleep(_STATUS_POLL_INTERVAL)
                async with session.get(
                    status_url,
                    params={"fields": "status_code", "access_token": access_token},
                ) as resp:
                    data = await resp.json()
                    status = data.get("status_code")
                    if status == "FINISHED":
                        break
                    if status == "ERROR":
                        raise RuntimeError(f"IG container processing failed: {data}")
            else:
                raise RuntimeError("IG container processing timed out")

            # Step 3: Publish
            publish_url = f"{base_url}/{ig_user_id}/media_publish"
            async with session.post(
                publish_url,
                params={"creation_id": container_id, "access_token": access_token},
            ) as resp:
                data = await resp.json()
                if "id" not in data:
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"IG publish error ({resp.status}): {error_msg}")
                media_id = data["id"]

        return UploadResult(
            platform=self.platform_name,
            video_id=media_id,
            success=True,
            url=f"https://www.instagram.com/reel/{media_id}/",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
