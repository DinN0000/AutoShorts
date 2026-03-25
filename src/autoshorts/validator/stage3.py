"""Stage 3: Final validation — determine upload action based on cumulative risk.

Optionally runs Claude Vision analysis on the video file to detect
visual copyright risks (logos, watermarks, copyrighted characters).
The vision score is merged with the existing risk score for the final decision.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from autoshorts.common.models import ValidationResult

logger = logging.getLogger(__name__)

# Weight for merging vision score with existing risk score
VISION_WEIGHT = 0.3
EXISTING_WEIGHT = 0.7


@dataclass
class FinalCheckInput:
    """Input for final validation stage."""

    video_id: str
    risk_score: int
    risk_reasons: list[str] = field(default_factory=list)
    video_path: str | None = None


class FinalValidator:
    """Makes final upload/reject decision based on cumulative risk score.

    If video_path is provided, runs Claude Vision frame analysis and
    merges the vision score with the existing risk score.
    """

    def check(self, input: FinalCheckInput) -> ValidationResult:
        """Determine action based on risk score (+ optional vision analysis).

        Scoring:
        - If video_path provided: merged = existing*0.7 + vision*0.3
        - If no video_path: uses existing risk_score as-is

        Decision thresholds (on final merged score):
        - 0-10: auto_upload (passed=True)
        - 11-30: openclaw_review (passed=True)
        - 31+: auto_reject (passed=False)
        """
        score = input.risk_score
        reasons = list(input.risk_reasons)
        vision_details: dict = {}

        # Run vision analysis if video path is provided
        if input.video_path and Path(input.video_path).exists():
            vision_result = self._run_vision_analysis(input.video_path)
            vision_details = vision_result
            vision_score = vision_result.get("vision_score", 0)

            if vision_score > 0:
                merged = int(score * EXISTING_WEIGHT + vision_score * VISION_WEIGHT)
                logger.info(
                    "Vision merge: existing=%d, vision=%d, merged=%d",
                    score,
                    vision_score,
                    merged,
                )
                score = merged

                # Add vision issues to reasons
                for issue in vision_result.get("issues", []):
                    reasons.append(f"vision: {issue}")

        if score <= 10:
            action = "auto_upload"
            passed = True
        elif score <= 30:
            action = "openclaw_review"
            passed = True
        else:
            action = "auto_reject"
            passed = False

        details: dict = {"action": action}
        if vision_details:
            details["vision"] = vision_details

        return ValidationResult(
            video_id=input.video_id,
            stage="final",
            passed=passed,
            score=score,
            reasons=reasons,
            details=details,
        )

    def _run_vision_analysis(self, video_path: str) -> dict:
        """Run Claude Vision analysis on video frames."""
        try:
            from autoshorts.validator.vision import analyze_video

            return analyze_video(video_path)
        except Exception as e:
            logger.error("Vision analysis failed: %s", e)
            return {"vision_score": 0, "issues": [], "summary": f"Error: {e}"}
