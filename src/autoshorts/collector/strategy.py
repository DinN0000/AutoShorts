"""Adaptive search strategy engine."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SearchStrategy:
    """Configurable search strategy parameters."""

    keywords: list[str] = field(default_factory=list)
    prefer_recent: bool = False
    prefer_unpopular: bool = False
    prefer_outdoor: bool = False
    prefer_cc_creators: bool = False
    platform_weights: dict[str, float] = field(default_factory=dict)

    @classmethod
    def default(cls) -> SearchStrategy:
        """Create a default strategy with Chinese animal keywords."""
        return cls(
            keywords=[
                "可爱动物",
                "猫咪",
                "狗狗",
                "小猫",
                "小狗",
                "萌宠",
                "宠物日常",
                "动物搞笑",
            ],
            prefer_recent=False,
            prefer_unpopular=False,
            prefer_outdoor=False,
            prefer_cc_creators=False,
            platform_weights={
                "douyin": 1.0,
                "bilibili": 1.0,
                "kuaishou": 1.0,
                "xiaohongshu": 1.0,
            },
        )

    def save(self, path: Path) -> None:
        """Save strategy to a JSON file."""
        data = {
            "keywords": self.keywords,
            "prefer_recent": self.prefer_recent,
            "prefer_unpopular": self.prefer_unpopular,
            "prefer_outdoor": self.prefer_outdoor,
            "prefer_cc_creators": self.prefer_cc_creators,
            "platform_weights": self.platform_weights,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> SearchStrategy:
        """Load strategy from a JSON file."""
        data = json.loads(path.read_text())
        return cls(
            keywords=data["keywords"],
            prefer_recent=data["prefer_recent"],
            prefer_unpopular=data["prefer_unpopular"],
            prefer_outdoor=data["prefer_outdoor"],
            prefer_cc_creators=data["prefer_cc_creators"],
            platform_weights=data["platform_weights"],
        )


@dataclass
class RejectionStats:
    """Tracks rejection statistics for strategy adjustment."""

    total_collected: int = 0
    total_rejected: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    @property
    def rejection_rate(self) -> float:
        """Return the rejection rate as a fraction between 0 and 1."""
        if self.total_collected == 0:
            return 0.0
        return self.total_rejected / self.total_collected

    @property
    def top_reason(self) -> str | None:
        """Return the most common rejection reason, or None if no rejections."""
        if not self.reasons:
            return None
        return max(self.reasons, key=self.reasons.get)  # type: ignore[arg-type]


# Mapping from rejection reason to strategy adjustments.
# Each value is a dict of SearchStrategy boolean fields to set to True.
REASON_ADJUSTMENTS: dict[str, dict[str, bool]] = {
    "already_on_youtube": {
        "prefer_recent": True,
        "prefer_unpopular": True,
    },
    "license_unclear": {
        "prefer_cc_creators": True,
    },
    "brand_logo": {
        "prefer_outdoor": True,
    },
}


class StrategyEngine:
    """Engine that adjusts search strategy based on rejection feedback."""

    def __init__(self, strategy: SearchStrategy | None = None) -> None:
        self.strategy = strategy or SearchStrategy.default()

    def adjust(self, stats: RejectionStats) -> SearchStrategy:
        """Adjust the search strategy based on rejection statistics.

        Only adjusts if rejection rate exceeds 50%. Changes search direction
        (not filters) based on the top rejection reason.
        """
        if stats.rejection_rate <= 0.5:
            return self.strategy

        top = stats.top_reason
        if top and top in REASON_ADJUSTMENTS:
            adjustments = REASON_ADJUSTMENTS[top]
            for attr, value in adjustments.items():
                setattr(self.strategy, attr, value)

        return self.strategy
