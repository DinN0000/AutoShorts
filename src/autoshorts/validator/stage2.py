"""Stage 2: Transform validation — check that sufficient transformation was applied."""

from __future__ import annotations

from dataclasses import dataclass, field

from autoshorts.common.models import ValidationResult

SAFE_BGM_SOURCES = ["royalty_free", "original", "tts_only", "none"]


@dataclass
class EditManifest:
    """Describes the transformations applied to a video."""

    video_id: str
    original_duration: float
    edited_duration: float
    has_narration: bool = False
    has_new_storyline: bool = False
    visual_changes: list[str] = field(default_factory=list)
    audio_replaced: bool = False
    bgm_source: str = "unknown"
    metadata_title: str = ""
    metadata_description: str = ""
    credit_included: bool = False


class TransformValidator:
    """Validates that sufficient creative transformation has been applied."""

    def check(self, manifest: EditManifest) -> ValidationResult:
        """Evaluate transformation sufficiency.

        Transform score (higher = more transformation):
          - narration: +3
          - storyline: +3
          - audio_replaced: +2
          - visual_changes: min(count, 5)

        Risk penalties:
          - insufficient_transformation (score < 6): +50
          - bgm_not_royalty_free (unknown source): +40
          - too_few_visual_changes (< 3): +20
        """
        # Calculate transformation score
        transform_score = 0
        if manifest.has_narration:
            transform_score += 3
        if manifest.has_new_storyline:
            transform_score += 3
        if manifest.audio_replaced:
            transform_score += 2
        transform_score += min(len(manifest.visual_changes), 5)

        # Calculate risk score
        risk_score = 0
        reasons: list[str] = []

        if transform_score < 6:
            risk_score += 50
            reasons.append(f"insufficient_transformation: score={transform_score}")

        if manifest.bgm_source.lower() not in SAFE_BGM_SOURCES:
            risk_score += 40
            reasons.append(f"bgm_not_royalty_free: {manifest.bgm_source}")

        if len(manifest.visual_changes) < 3:
            risk_score += 20
            reasons.append(f"too_few_visual_changes: {len(manifest.visual_changes)}")

        passed = risk_score < 31

        return ValidationResult(
            video_id=manifest.video_id,
            stage="transform",
            passed=passed,
            score=risk_score,
            reasons=reasons,
            details={"transform_score": transform_score},
        )
