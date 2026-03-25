"""Bilibili platform adapter stub."""
from __future__ import annotations

from pathlib import Path

from .base import CollectResult, PlatformAdapter


class BilibiliAdapter(PlatformAdapter):
    """Adapter for collecting videos from Bilibili."""

    @property
    def platform_name(self) -> str:
        return "bilibili"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        raise NotImplementedError("Bilibili search not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        raise NotImplementedError("Bilibili download not yet implemented")
