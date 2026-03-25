from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime


class VideoStatus(str, Enum):
    RAW = "raw"
    SOURCE_VALIDATED = "source_validated"
    EDITED = "edited"
    TRANSFORM_VALIDATED = "transform_validated"
    FINAL_VALIDATED = "final_validated"
    LOCALIZED = "localized"
    UPLOADED = "uploaded"
    REJECTED = "rejected"


@dataclass
class VideoMeta:
    id: str
    platform: str
    source_url: str
    title: str
    author: str
    duration_seconds: float
    tags: list[str] = field(default_factory=list)
    status: VideoStatus = VideoStatus.RAW
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    license_info: str = ""
    rejection_reason: str = ""

    def save(self, path: Path) -> None:
        data = asdict(self)
        data["status"] = self.status.value
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> VideoMeta:
        data = json.loads(path.read_text())
        data["status"] = VideoStatus(data["status"])
        return cls(**data)


@dataclass
class ValidationResult:
    video_id: str
    stage: str  # "source", "transform", "final"
    passed: bool
    score: int  # 0-100, lower is safer
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> ValidationResult:
        return cls(**json.loads(path.read_text()))
