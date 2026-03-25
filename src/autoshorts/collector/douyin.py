"""Douyin (TikTok China) platform adapter stub."""
from __future__ import annotations

from pathlib import Path

from .base import CollectResult, PlatformAdapter


class DouyinAdapter(PlatformAdapter):
    """Adapter for collecting videos from Douyin."""

    @property
    def platform_name(self) -> str:
        return "douyin"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        raise NotImplementedError("Douyin search not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        raise NotImplementedError("Douyin download not yet implemented")
