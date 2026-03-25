"""Pipeline runner — orchestrates stage execution."""

import uuid
from pathlib import Path

from .state import STAGE_ORDER, PipelineState, StageStatus

STATE_FILE = Path("data/pipeline_state.json")


def run_pipeline() -> PipelineState:
    """Run the full pipeline, advancing through each stage.

    Currently uses placeholder execution for each stage.
    """
    run_id = uuid.uuid4().hex[:12]
    state = PipelineState.new(run_id)

    for stage in STAGE_ORDER:
        state.advance(stage, StageStatus.IN_PROGRESS)
        # Placeholder: actual stage execution would go here
        state.advance(stage, StageStatus.COMPLETED)

    state.save(STATE_FILE)
    return state


def get_status() -> dict:
    """Return current pipeline status for heartbeat monitoring."""
    if not STATE_FILE.exists():
        return {"status": "no_runs", "state": None}

    state = PipelineState.load(STATE_FILE)
    return {
        "status": "ok",
        "run_id": state.run_id,
        "current_stage": state.current_stage,
        "stages": {k: v.value for k, v in state.stages.items()},
        "started_at": state.started_at,
        "updated_at": state.updated_at,
    }
