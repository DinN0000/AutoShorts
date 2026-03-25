"""Integration tests — verify the full validation pipeline and strategy adjustment cycle."""
from pathlib import Path

from autoshorts.pipeline.state import PipelineState, StageStatus
from autoshorts.common.models import VideoMeta, VideoStatus
from autoshorts.validator.stage1 import SourceValidator
from autoshorts.validator.stage2 import TransformValidator, EditManifest
from autoshorts.validator.stage3 import FinalValidator, FinalCheckInput
from autoshorts.editor.transforms import EditConfig, build_ffmpeg_filters
from autoshorts.collector.strategy import SearchStrategy, StrategyEngine, RejectionStats


def test_full_validation_pipeline():
    """Test the 3-stage validation flow end-to-end (without actual video files)."""

    # Stage 1: Source validation
    meta = VideoMeta(
        id="integration_test_001",
        platform="douyin",
        source_url="https://example.com",
        title="小猫在花园里玩耍",
        author="catgarden",
        duration_seconds=25,
        tags=["cat", "garden", "outdoor"],
        license_info="cc-by",
    )
    source_validator = SourceValidator()
    s1_result = source_validator.check_metadata(meta)
    assert s1_result.passed, f"Stage 1 should pass: {s1_result.reasons}"

    # Stage 2: Transform validation
    manifest = EditManifest(
        video_id=meta.id,
        original_duration=25.0,
        edited_duration=23.0,
        has_narration=True,
        has_new_storyline=True,
        visual_changes=["speed_change", "flip", "crop", "color_grade", "zoom"],
        audio_replaced=True,
        bgm_source="royalty_free",
    )
    transform_validator = TransformValidator()
    s2_result = transform_validator.check(manifest)
    assert s2_result.passed, f"Stage 2 should pass: {s2_result.reasons}"

    # Stage 3: Final validation
    final_input = FinalCheckInput(
        video_id=meta.id,
        risk_score=5,
        risk_reasons=[],
    )
    final_validator = FinalValidator()
    s3_result = final_validator.check(final_input)
    assert s3_result.passed
    assert s3_result.details["action"] == "auto_upload"


def test_validation_pipeline_rejects_unsafe_video():
    """Test that the pipeline correctly rejects a copyright-risky video."""

    meta = VideoMeta(
        id="integration_test_002",
        platform="bilibili",
        source_url="https://example.com",
        title="Cat playing with Nike shoes in Disney store",
        author="brandlover",
        duration_seconds=30,
        tags=["nike", "disney", "cat"],
    )
    source_validator = SourceValidator()
    s1_result = source_validator.check_metadata(meta)
    assert not s1_result.passed, "Should reject video with brand keywords"
    assert any("brand_detected" in r for r in s1_result.reasons)


def test_strategy_adjustment_cycle(tmp_path):
    """Test that high rejection rates trigger strategy adjustments."""
    engine = StrategyEngine()

    stats = RejectionStats(
        total_collected=100,
        total_rejected=85,
        reasons={"already_on_youtube": 50, "brand_detected": 20, "license_unclear": 15},
    )

    adjusted = engine.adjust(stats)
    assert adjusted.prefer_unpopular is True


def test_pipeline_state_full_cycle(tmp_path):
    """Test pipeline state transitions through all stages."""
    state = PipelineState.new("integration_run")
    state_file = tmp_path / "state.json"

    for stage in ["collect", "validate_source", "edit", "validate_transform",
                   "translate", "validate_final", "upload"]:
        assert state.current_stage == stage
        state.advance(stage, StageStatus.IN_PROGRESS)
        state.advance(stage, StageStatus.COMPLETED)
        state.save(state_file)

    loaded = PipelineState.load(state_file)
    assert all(s == StageStatus.COMPLETED for s in loaded.stages.values())


def test_edit_config_produces_valid_ffmpeg_filters():
    """Test that random strong config produces non-empty FFmpeg filter string."""
    config = EditConfig.random_strong()
    filters = build_ffmpeg_filters(config)
    assert len(filters) > 0
    # Should have at least 2 filters
    assert "," in filters or len(filters) > 10
