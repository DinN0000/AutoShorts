"""Tests for Stage 3: Final validation with Vision integration."""

from unittest.mock import patch, MagicMock

from autoshorts.validator.stage3 import FinalCheckInput, FinalValidator


class TestFinalValidator:
    def setup_method(self):
        self.validator = FinalValidator()

    def test_auto_upload_low_score(self):
        inp = FinalCheckInput(video_id="test-001", risk_score=5)
        result = self.validator.check(inp)
        assert result.passed
        assert result.details["action"] == "auto_upload"

    def test_manual_review_mid_score(self):
        inp = FinalCheckInput(
            video_id="test-002",
            risk_score=20,
            risk_reasons=["too_few_visual_changes"],
        )
        result = self.validator.check(inp)
        assert result.passed
        assert result.details["action"] == "openclaw_review"

    def test_auto_reject_high_score(self):
        inp = FinalCheckInput(
            video_id="test-003",
            risk_score=55,
            risk_reasons=["brand_detected", "insufficient_transformation"],
        )
        result = self.validator.check(inp)
        assert not result.passed
        assert result.details["action"] == "auto_reject"

    def test_video_path_optional_default_none(self):
        inp = FinalCheckInput(video_id="test-004", risk_score=5)
        assert inp.video_path is None

    def test_video_path_nonexistent_skips_vision(self):
        """Non-existent video path should skip vision and use original score."""
        inp = FinalCheckInput(
            video_id="test-005",
            risk_score=5,
            video_path="/nonexistent/video.mp4",
        )
        result = self.validator.check(inp)
        assert result.passed
        assert result.details["action"] == "auto_upload"
        assert "vision" not in result.details

    @patch("autoshorts.validator.stage3.Path")
    @patch("autoshorts.validator.vision.analyze_video")
    def test_vision_merges_score(self, mock_analyze, mock_path):
        """Vision score should be merged with existing risk score."""
        mock_path.return_value.exists.return_value = True
        mock_analyze.return_value = {
            "vision_score": 80,
            "issues": ["logo detected"],
            "summary": "Nike logo visible",
        }
        inp = FinalCheckInput(
            video_id="test-006",
            risk_score=10,
            video_path="/fake/video.mp4",
        )
        result = self.validator.check(inp)
        # merged = 10*0.7 + 80*0.3 = 7 + 24 = 31
        assert result.score == 31
        assert not result.passed
        assert result.details["action"] == "auto_reject"
        assert result.details["vision"]["vision_score"] == 80
        assert "vision: logo detected" in result.reasons

    @patch("autoshorts.validator.stage3.Path")
    @patch("autoshorts.validator.vision.analyze_video")
    def test_vision_zero_score_no_change(self, mock_analyze, mock_path):
        """Vision score of 0 should not change the existing score."""
        mock_path.return_value.exists.return_value = True
        mock_analyze.return_value = {
            "vision_score": 0,
            "issues": [],
            "summary": "Clean video",
        }
        inp = FinalCheckInput(
            video_id="test-007",
            risk_score=5,
            video_path="/fake/video.mp4",
        )
        result = self.validator.check(inp)
        assert result.score == 5
        assert result.passed
        assert result.details["action"] == "auto_upload"

    @patch("autoshorts.validator.stage3.Path")
    @patch("autoshorts.validator.vision.analyze_video")
    def test_vision_upgrades_to_review(self, mock_analyze, mock_path):
        """Moderate vision risk should push a low score into review range."""
        mock_path.return_value.exists.return_value = True
        mock_analyze.return_value = {
            "vision_score": 50,
            "issues": ["watermark detected"],
            "summary": "Faint watermark",
        }
        inp = FinalCheckInput(
            video_id="test-008",
            risk_score=8,
            video_path="/fake/video.mp4",
        )
        result = self.validator.check(inp)
        # merged = 8*0.7 + 50*0.3 = 5.6 + 15 = 20.6 -> 20
        assert result.score == 20
        assert result.passed
        assert result.details["action"] == "openclaw_review"

    @patch("autoshorts.validator.stage3.Path")
    def test_vision_exception_handled(self, mock_path):
        """Vision analysis errors should be caught gracefully."""
        mock_path.return_value.exists.return_value = True
        with patch(
            "autoshorts.validator.stage3.FinalValidator._run_vision_analysis",
            side_effect=Exception("API down"),
        ):
            # If _run_vision_analysis raises, it should still work
            # But since we catch in check(), let's test the inner method
            pass

        # Test the fallback path via _run_vision_analysis directly
        with patch(
            "autoshorts.validator.vision.analyze_video",
            side_effect=Exception("boom"),
        ):
            result = self.validator._run_vision_analysis("/fake/path")
            assert result["vision_score"] == 0


class TestVisionModule:
    """Tests for the vision extraction and analysis module."""

    def test_extract_frames_missing_opencv(self):
        """Should return empty list when opencv not available."""
        with patch.dict("sys.modules", {"cv2": None}):
            # Re-import would fail, but the function handles ImportError
            from autoshorts.validator.vision import extract_frames

            # With a non-existent file, should return empty
            result = extract_frames("/nonexistent/video.mp4")
            assert result == []

    def test_analyze_frames_no_key(self):
        """Should return zero score when no API key configured."""
        with patch.dict("os.environ", {}, clear=True):
            from autoshorts.validator.vision import analyze_frames_with_vision

            result = analyze_frames_with_vision([b"fake_frame"])
            assert result["vision_score"] == 0
            assert "not configured" in result["summary"]

    def test_analyze_frames_empty(self):
        """Empty frame list should return zero score."""
        from autoshorts.validator.vision import analyze_frames_with_vision

        result = analyze_frames_with_vision([])
        assert result["vision_score"] == 0

    def test_analyze_frames_success(self):
        """Successful API call should parse response correctly."""
        import os
        import sys

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"vision_score": 45, "issues": ["watermark"], "summary": "Has watermark"}'
            )
        ]
        mock_client.messages.create.return_value = mock_response

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            from autoshorts.validator.vision import analyze_frames_with_vision

            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = analyze_frames_with_vision([b"fake_frame_data"])

        assert result["vision_score"] == 45
        assert "watermark" in result["issues"]
