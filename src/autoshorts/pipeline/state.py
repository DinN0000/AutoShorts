"""Pipeline state management."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


STAGE_ORDER = [
    "collect",
    "validate_source",
    "edit",
    "validate_transform",
    "translate",
    "validate_final",
    "upload",
]


class StageStatus(str, Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineState:
    """Tracks the state of a pipeline run."""

    run_id: str
    current_stage: str
    stages: dict[str, StageStatus]
    started_at: str = ""
    updated_at: str = ""
    stats: dict = field(default_factory=dict)

    @classmethod
    def new(cls, run_id: str) -> "PipelineState":
        """Create a new pipeline state with all stages PENDING."""
        now = datetime.now(timezone.utc).isoformat()
        stages = {stage: StageStatus.PENDING for stage in STAGE_ORDER}
        return cls(
            run_id=run_id,
            current_stage=STAGE_ORDER[0],
            stages=stages,
            started_at=now,
            updated_at=now,
        )

    def advance(self, stage: str, status: StageStatus) -> None:
        """Update a stage's status and advance current_stage on COMPLETED."""
        if stage not in self.stages:
            raise ValueError(f"Unknown stage: {stage}")

        self.stages[stage] = status
        self.updated_at = datetime.now(timezone.utc).isoformat()

        if status == StageStatus.COMPLETED:
            idx = STAGE_ORDER.index(stage)
            if idx + 1 < len(STAGE_ORDER):
                self.current_stage = STAGE_ORDER[idx + 1]

    def save(self, path: Path) -> None:
        """Save state to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "run_id": self.run_id,
            "current_stage": self.current_stage,
            "stages": {k: v.value for k, v in self.stages.items()},
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "stats": self.stats,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> "PipelineState":
        """Load state from a JSON file."""
        data = json.loads(path.read_text())
        stages = {k: StageStatus(v) for k, v in data["stages"].items()}
        return cls(
            run_id=data["run_id"],
            current_stage=data["current_stage"],
            stages=stages,
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
            stats=data.get("stats", {}),
        )
