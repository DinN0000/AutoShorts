"""Tests for pipeline state management."""

from pathlib import Path

from autoshorts.pipeline.state import STAGE_ORDER, PipelineState, StageStatus


def test_initial_state():
    """New state should have all stages PENDING with current='collect'."""
    state = PipelineState.new("test-run-1")
    assert state.current_stage == "collect"
    for stage in STAGE_ORDER:
        assert state.stages[stage] == StageStatus.PENDING


def test_advance_stage():
    """Completing 'collect' should advance current_stage to 'validate_source'."""
    state = PipelineState.new("test-run-2")
    state.advance("collect", StageStatus.COMPLETED)
    assert state.stages["collect"] == StageStatus.COMPLETED
    assert state.current_stage == "validate_source"


def test_save_and_load(tmp_path: Path):
    """State should survive a save/load roundtrip."""
    state = PipelineState.new("test-run-3")
    state.advance("collect", StageStatus.COMPLETED)

    path = tmp_path / "state.json"
    state.save(path)

    loaded = PipelineState.load(path)
    assert loaded.run_id == state.run_id
    assert loaded.current_stage == state.current_stage
    assert loaded.stages["collect"] == StageStatus.COMPLETED
    for stage in STAGE_ORDER[1:]:
        assert loaded.stages[stage] == StageStatus.PENDING
