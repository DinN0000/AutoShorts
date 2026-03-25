"""Stage 3: Final validation — determine upload action based on cumulative risk."""

from __future__ import annotations

from dataclasses import dataclass, field

from autoshorts.common.models import ValidationResult


@dataclass
class FinalCheckInput:
    """Input for final validation stage."""

    video_id: str
    risk_score: int
    risk_reasons: list[str] = field(default_factory=list)


class FinalValidator:
    """Makes final upload/reject decision based on cumulative risk score."""

    def check(self, input: FinalCheckInput) -> ValidationResult:
        """Determine action based on risk score.

        - 0-10: auto_upload (passed=True)
        - 11-30: openclaw_review (passed=True)
        - 31+: auto_reject (passed=False)
        """
        score = input.risk_score

        if score <= 10:
            action = "auto_upload"
            passed = True
        elif score <= 30:
            action = "openclaw_review"
            passed = True
        else:
            action = "auto_reject"
            passed = False

        return ValidationResult(
            video_id=input.video_id,
            stage="final",
            passed=passed,
            score=score,
            reasons=input.risk_reasons,
            details={"action": action},
        )
