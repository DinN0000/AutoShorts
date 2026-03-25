"""Xiaohongshu (Little Red Book) platform adapter stub."""
from __future__ import annotations

from pathlib import Path

from .base import CollectResult, PlatformAdapter


class XiaohongshuAdapter(PlatformAdapter):
    """Adapter for collecting videos from Xiaohongshu."""

    @property
    def platform_name(self) -> str:
        return "xiaohongshu"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        raise NotImplementedError("Xiaohongshu search not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        raise NotImplementedError("Xiaohongshu download not yet implemented")
