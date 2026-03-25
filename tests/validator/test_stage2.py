"""Tests for Stage 2: Transform validation."""

from autoshorts.validator.stage2 import EditManifest, TransformValidator


class TestTransformValidator:
    def setup_method(self):
        self.validator = TransformValidator()

    def test_rejects_insufficient_transformation(self):
        manifest = EditManifest(
            video_id="test-001",
            original_duration=60.0,
            edited_duration=55.0,
            has_narration=False,
            has_new_storyline=False,
            visual_changes=["subtitles"],
            audio_replaced=False,
            bgm_source="royalty_free",
        )
        result = self.validator.check(manifest)
        assert not result.passed
        assert any("insufficient_transformation" in r for r in result.reasons)

    def test_accepts_high_transformation(self):
        manifest = EditManifest(
            video_id="test-002",
            original_duration=60.0,
            edited_duration=45.0,
            has_narration=True,
            has_new_storyline=True,
            visual_changes=["crop", "color_grade", "text_overlay", "transition", "zoom"],
            audio_replaced=True,
            bgm_source="royalty_free",
        )
        result = self.validator.check(manifest)
        assert result.passed
        assert result.score < 31

    def test_rejects_unknown_bgm_source(self):
        manifest = EditManifest(
            video_id="test-003",
            original_duration=60.0,
            edited_duration=45.0,
            has_narration=True,
            has_new_storyline=True,
            visual_changes=["crop", "color_grade", "text_overlay"],
            audio_replaced=True,
            bgm_source="unknown_source",
        )
        result = self.validator.check(manifest)
        assert not result.passed
        assert any("bgm_not_royalty_free" in r for r in result.reasons)
