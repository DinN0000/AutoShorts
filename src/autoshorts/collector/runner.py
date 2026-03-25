"""Runner that orchestrates collection using adapters and strategy."""
from __future__ import annotations

from pathlib import Path

from .base import CollectResult, PlatformAdapter
from .strategy import RejectionStats, SearchStrategy, StrategyEngine


class CollectorRunner:
    """Runs collection across multiple platform adapters using a search strategy."""

    def __init__(
        self,
        adapters: list[PlatformAdapter],
        strategy: SearchStrategy | None = None,
    ) -> None:
        self.adapters = adapters
        self.engine = StrategyEngine(strategy)
        self.stats = RejectionStats()

    async def collect(self, output_dir: Path, limit: int = 10) -> list[CollectResult]:
        """Collect videos from all adapters using the current strategy.

        Args:
            output_dir: Directory to save downloaded videos.
            limit: Maximum number of videos to collect per adapter.

        Returns:
            List of collected results.
        """
        results: list[CollectResult] = []
        strategy = self.engine.strategy

        for adapter in self.adapters:
            weight = strategy.platform_weights.get(adapter.platform_name, 1.0)
            adapter_limit = max(1, int(limit * weight))

            try:
                found = await adapter.search(strategy.keywords, adapter_limit)
                for item in found:
                    try:
                        path = await adapter.download(item, output_dir)
                        item.video_path = path
                        results.append(item)
                        self.stats.total_collected += 1
                    except Exception:
                        self.stats.total_collected += 1
                        self.stats.total_rejected += 1
            except NotImplementedError:
                continue

        return results

    def feedback(self, reason: str) -> None:
        """Record a rejection and adjust strategy if needed."""
        self.stats.total_collected += 1
        self.stats.total_rejected += 1
        self.stats.reasons[reason] = self.stats.reasons.get(reason, 0) + 1
        self.engine.adjust(self.stats)
