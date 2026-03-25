"""Kuaishou platform adapter stub."""
from __future__ import annotations

from pathlib import Path

from .base import CollectResult, PlatformAdapter


class KuaishouAdapter(PlatformAdapter):
    """Adapter for collecting videos from Kuaishou."""

    @property
    def platform_name(self) -> str:
        return "kuaishou"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        raise NotImplementedError("Kuaishou search not yet implemented")

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        raise NotImplementedError("Kuaishou download not yet implemented")
