"""Tests for Stage 1: Source validation."""

from autoshorts.common.models import VideoMeta
from autoshorts.validator.stage1 import SourceValidator


def _make_meta(**kwargs) -> VideoMeta:
    defaults = dict(
        id="test-001",
        platform="pexels",
        source_url="https://example.com/video",
        title="Test Video",
        author="tester",
        duration_seconds=30.0,
        tags=[],
        license_info="",
    )
    defaults.update(kwargs)
    return VideoMeta(**defaults)


class TestSourceValidator:
    def setup_method(self):
        self.validator = SourceValidator()

    def test_rejects_video_with_brand_logo(self):
        meta = _make_meta(
            title="Cat in Nike store",
            tags=["nike", "cat"],
        )
        result = self.validator.check_metadata(meta)
        assert not result.passed
        assert result.score >= 50
        assert any("brand_detected" in r for r in result.reasons)

    def test_accepts_clean_video(self):
        meta = _make_meta(
            title="野外小猫玩耍",
            license_info="cc-by",
        )
        result = self.validator.check_metadata(meta)
        assert result.passed
        assert result.score < 31

    def test_rejects_too_short_video(self):
        meta = _make_meta(duration_seconds=3)
        result = self.validator.check_metadata(meta)
        assert not result.passed
        assert result.score >= 100
        assert any("too_short" in r for r in result.reasons)
