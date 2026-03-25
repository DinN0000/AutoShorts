"""Tests for collector base module."""
from __future__ import annotations

import pytest

from autoshorts.collector.base import CollectResult, PlatformAdapter


class TestCollectResult:
    def test_create_minimal(self):
        result = CollectResult(
            video_id="abc123",
            platform="douyin",
            source_url="https://douyin.com/video/abc123",
            title="Cute cat",
            author="user1",
            duration_seconds=30.0,
            video_path=None,
        )
        assert result.video_id == "abc123"
        assert result.platform == "douyin"
        assert result.source_url == "https://douyin.com/video/abc123"
        assert result.title == "Cute cat"
        assert result.author == "user1"
        assert result.duration_seconds == 30.0
        assert result.video_path is None
        assert result.metadata == {}
        assert result.license_info == "unknown"

    def test_create_with_metadata(self):
        result = CollectResult(
            video_id="xyz",
            platform="bilibili",
            source_url="https://bilibili.com/xyz",
            title="Dog video",
            author="user2",
            duration_seconds=60.5,
            video_path=None,
            metadata={"tags": ["dog", "cute"]},
            license_info="CC-BY",
        )
        assert result.metadata == {"tags": ["dog", "cute"]}
        assert result.license_info == "CC-BY"


class TestPlatformAdapter:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            PlatformAdapter()  # type: ignore[abstract]
