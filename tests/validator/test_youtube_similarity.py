"""Tests for YouTube similarity checker and hard gate integration."""

from unittest.mock import patch, MagicMock

from autoshorts.common.models import VideoMeta
from autoshorts.validator.stage1 import SourceValidator
from autoshorts.validator.youtube_similarity import (
    SIMILARITY_THRESHOLD,
    YouTubeMatch,
    check_youtube_similarity,
    compute_text_similarity,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_meta(**kwargs) -> VideoMeta:
    defaults = dict(
        id="test-yt-001",
        platform="douyin",
        source_url="https://example.com/video",
        title="Cute cat playing in garden",
        author="tester",
        duration_seconds=30.0,
        tags=["cat", "cute", "garden"],
        license_info="cc-by",
    )
    defaults.update(kwargs)
    return VideoMeta(**defaults)


def _make_match(similarity: float, **kwargs) -> YouTubeMatch:
    defaults = dict(
        video_id="yt-abc123",
        title="Cute cat playing in garden",
        tags=["cat", "cute"],
        thumbnail_url="https://img.youtube.com/thumb.jpg",
        text_similarity=similarity,
        thumbnail_similarity=0.0,
        combined_similarity=similarity,
    )
    defaults.update(kwargs)
    return YouTubeMatch(**defaults)


# ---------------------------------------------------------------------------
# Text similarity tests
# ---------------------------------------------------------------------------

class TestTextSimilarity:
    def test_identical_titles_high_score(self):
        score = compute_text_similarity(
            "Cute cat playing", ["cat", "cute"],
            "Cute cat playing", ["cat", "cute"],
        )
        assert score >= 90

    def test_different_titles_low_score(self):
        score = compute_text_similarity(
            "Cute cat playing", ["cat"],
            "Race car driving fast", ["car", "racing"],
        )
        assert score < 50

    def test_similar_titles_moderate_score(self):
        score = compute_text_similarity(
            "Cat playing in garden", ["cat", "garden"],
            "Kitten playing in the garden", ["kitten", "garden"],
        )
        # Should be moderate-to-high due to shared words
        assert score > 40

    def test_empty_tags_still_compares_titles(self):
        score = compute_text_similarity(
            "Cute cat playing", [],
            "Cute cat playing", [],
        )
        # Title alone should give high score
        assert score >= 60

    def test_tag_overlap_boosts_score(self):
        score_no_tags = compute_text_similarity(
            "video", [], "video", [],
        )
        score_with_tags = compute_text_similarity(
            "video", ["cat", "cute", "funny"],
            "video", ["cat", "cute", "funny"],
        )
        assert score_with_tags >= score_no_tags


# ---------------------------------------------------------------------------
# check_youtube_similarity tests
# ---------------------------------------------------------------------------

class TestCheckYouTubeSimilarity:
    @patch("autoshorts.validator.youtube_similarity.search_youtube_similar")
    def test_duplicate_detected_above_threshold(self, mock_search):
        mock_search.return_value = [_make_match(80.0)]
        is_dup, max_sim, matches = check_youtube_similarity(
            "Cute cat", ["cat"], api_key="fake"
        )
        assert is_dup is True
        assert max_sim >= SIMILARITY_THRESHOLD
        assert len(matches) == 1

    @patch("autoshorts.validator.youtube_similarity.search_youtube_similar")
    def test_no_duplicate_below_threshold(self, mock_search):
        mock_search.return_value = [_make_match(50.0)]
        is_dup, max_sim, matches = check_youtube_similarity(
            "Cute cat", ["cat"], api_key="fake"
        )
        assert is_dup is False
        assert max_sim < SIMILARITY_THRESHOLD

    @patch("autoshorts.validator.youtube_similarity.search_youtube_similar")
    def test_no_results_not_duplicate(self, mock_search):
        mock_search.return_value = []
        is_dup, max_sim, matches = check_youtube_similarity(
            "Unique title", [], api_key="fake"
        )
        assert is_dup is False
        assert max_sim == 0.0
        assert matches == []

    @patch("autoshorts.validator.youtube_similarity.search_youtube_similar")
    def test_exact_threshold_is_duplicate(self, mock_search):
        mock_search.return_value = [_make_match(75.0)]
        is_dup, max_sim, _ = check_youtube_similarity(
            "Test", [], api_key="fake"
        )
        assert is_dup is True

    def test_no_api_key_returns_empty(self):
        with patch("autoshorts.validator.youtube_similarity._load_api_key", return_value=None):
            is_dup, max_sim, matches = check_youtube_similarity(
                "Test", [], api_key=None
            )
        assert is_dup is False
        assert matches == []


# ---------------------------------------------------------------------------
# Hard gate integration in SourceValidator
# ---------------------------------------------------------------------------

class TestHardGateIntegration:
    @patch("autoshorts.validator.stage1.check_youtube_similarity")
    def test_hard_gate_rejects_similar_video(self, mock_check):
        mock_check.return_value = (True, 85.0, [_make_match(85.0)])
        validator = SourceValidator()
        meta = _make_meta(license_info="")  # no CC bonus
        result = validator.check_metadata(meta)

        assert not result.passed
        assert result.score >= 100
        assert any("youtube_duplicate" in r for r in result.reasons)
        assert "youtube_similarity" in result.details

    @patch("autoshorts.validator.stage1.check_youtube_similarity")
    def test_no_duplicate_passes_normally(self, mock_check):
        mock_check.return_value = (False, 30.0, [_make_match(30.0)])
        validator = SourceValidator()
        meta = _make_meta()
        result = validator.check_metadata(meta)

        assert result.passed
        assert not any("youtube_duplicate" in r for r in result.reasons)

    @patch("autoshorts.validator.stage1.check_youtube_similarity")
    def test_hard_gate_overrides_clean_video(self, mock_check):
        """Even a perfectly clean video should be rejected if YouTube duplicate.

        CC license gives -20, but hard gate +100 still results in score 80,
        well above the pass threshold of 31.
        """
        mock_check.return_value = (True, 90.0, [_make_match(90.0)])
        validator = SourceValidator()
        meta = _make_meta(
            title="Perfect original video",
            tags=[],
            license_info="cc-by",
            duration_seconds=60.0,
        )
        result = validator.check_metadata(meta)

        # Hard gate +100, CC bonus -20 = 80, still way above threshold 31
        assert not result.passed
        assert result.score >= 31  # above pass threshold

    @patch("autoshorts.validator.stage1.check_youtube_similarity")
    def test_hard_gate_details_recorded(self, mock_check):
        top_match = _make_match(
            80.0,
            video_id="yt-xyz789",
            title="Similar Cat Video",
            text_similarity=82.0,
            thumbnail_similarity=75.0,
        )
        mock_check.return_value = (True, 80.0, [top_match])
        validator = SourceValidator()
        meta = _make_meta()
        result = validator.check_metadata(meta)

        details = result.details["youtube_similarity"]
        assert details["max_similarity"] == 80.0
        assert details["threshold"] == SIMILARITY_THRESHOLD
        assert details["top_match_id"] == "yt-xyz789"
        assert details["top_match_title"] == "Similar Cat Video"

    @patch("autoshorts.validator.stage1.check_youtube_similarity")
    def test_api_unavailable_does_not_block(self, mock_check):
        """If YouTube API is unavailable, validation should continue normally."""
        mock_check.return_value = (False, 0.0, [])
        validator = SourceValidator()
        meta = _make_meta()
        result = validator.check_metadata(meta)

        # Should pass based on other checks alone
        assert result.passed

    @patch("autoshorts.validator.stage1.check_youtube_similarity")
    def test_existing_checks_still_work_with_hard_gate(self, mock_check):
        """Brand/duration/danger checks should still trigger alongside hard gate."""
        mock_check.return_value = (False, 0.0, [])
        validator = SourceValidator()
        meta = _make_meta(
            title="Cat in Nike store",
            tags=["nike"],
            duration_seconds=3.0,  # too short
        )
        result = validator.check_metadata(meta)

        assert not result.passed
        assert any("brand_detected" in r for r in result.reasons)
        assert any("too_short" in r for r in result.reasons)
