"""Tests for Stage 3: Final validation."""

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
