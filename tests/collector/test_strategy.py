"""Tests for collector strategy module."""
from __future__ import annotations

from pathlib import Path

from autoshorts.collector.strategy import (
    RejectionStats,
    SearchStrategy,
    StrategyEngine,
)


class TestSearchStrategy:
    def test_default_has_keywords(self):
        strategy = SearchStrategy.default()
        assert len(strategy.keywords) > 0
        assert isinstance(strategy.keywords, list)

    def test_save_load_roundtrip(self, tmp_path: Path):
        original = SearchStrategy.default()
        original.prefer_recent = True
        filepath = tmp_path / "strategy.json"
        original.save(filepath)

        loaded = SearchStrategy.load(filepath)
        assert loaded.keywords == original.keywords
        assert loaded.prefer_recent == original.prefer_recent
        assert loaded.prefer_unpopular == original.prefer_unpopular
        assert loaded.prefer_outdoor == original.prefer_outdoor
        assert loaded.prefer_cc_creators == original.prefer_cc_creators
        assert loaded.platform_weights == original.platform_weights


class TestStrategyEngine:
    def test_adjusts_on_high_rejection(self):
        engine = StrategyEngine()
        stats = RejectionStats(
            total_collected=10,
            total_rejected=8,
            reasons={"already_on_youtube": 8},
        )
        assert stats.rejection_rate > 0.5

        engine.adjust(stats)
        assert engine.strategy.prefer_recent is True
        assert engine.strategy.prefer_unpopular is True

    def test_no_adjust_on_low_rejection(self):
        engine = StrategyEngine()
        stats = RejectionStats(
            total_collected=10,
            total_rejected=3,
            reasons={"already_on_youtube": 3},
        )
        assert stats.rejection_rate < 0.5

        engine.adjust(stats)
        assert engine.strategy.prefer_recent is False
        assert engine.strategy.prefer_unpopular is False
