"""Threads uploader via Threads API (Meta)."""

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


class ThreadsUploader(PlatformUploader):
    """Upload video to Threads via Threads Publishing API."""

    @property
    def platform_name(self) -> str:
        return "threads"

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        schedule_time: Optional[str] = None,
    ) -> UploadResult:
        secrets = load_secrets("threads")
        access_token = secrets.get("access_token")
        user_id = secrets.get("user_id")
        if not access_token or not user_id:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing threads access_token or user_id in secrets",
            )
        video_url = secrets.get("video_host_url", "")
        if not video_url:
            return UploadResult(
                platform=self.platform_name,
                video_id="",
                success=False,
                error="Missing threads video_host_url in secrets (public URL required)",
            )

        async def _do_upload():
            return await self._upload_video(
                access_token, user_id, video_url, title, description, tags,
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
        user_id: str,
        video_url: str,
        title: str,
        description: str,
        tags: list[str],
    ) -> UploadResult:
        import aiohttp

        base_url = "https://graph.threads.net/v1.0"
        tag_str = " ".join(f"#{t}" for t in tags)
        text = f"{title}\n\n{description}\n\n{tag_str}".strip()

        async with aiohttp.ClientSession() as session:
            # Step 1: Create media container
            create_url = f"{base_url}/{user_id}/threads"
            params = {
                "media_type": "VIDEO",
                "video_url": video_url,
                "text": text[:500],
                "access_token": access_token,
            }
            async with session.post(create_url, params=params) as resp:
                data = await resp.json()
                if "id" not in data:
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"Threads container error ({resp.status}): {error_msg}")
                container_id = data["id"]

            # Step 2: Poll until ready
            status_url = f"{base_url}/{container_id}"
            for _ in range(_STATUS_POLL_MAX):
                await asyncio.sleep(_STATUS_POLL_INTERVAL)
                async with session.get(
                    status_url,
                    params={"fields": "status", "access_token": access_token},
                ) as resp:
                    data = await resp.json()
                    status = data.get("status")
                    if status == "FINISHED":
                        break
                    if status == "ERROR":
                        raise RuntimeError(f"Threads processing failed: {data}")
            else:
                raise RuntimeError("Threads container processing timed out")

            # Step 3: Publish
            publish_url = f"{base_url}/{user_id}/threads_publish"
            async with session.post(
                publish_url,
                params={"creation_id": container_id, "access_token": access_token},
            ) as resp:
                data = await resp.json()
                if "id" not in data:
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise RuntimeError(f"Threads publish error ({resp.status}): {error_msg}")
                media_id = data["id"]

        return UploadResult(
            platform=self.platform_name,
            video_id=media_id,
            success=True,
            url=f"https://www.threads.net/post/{media_id}",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
