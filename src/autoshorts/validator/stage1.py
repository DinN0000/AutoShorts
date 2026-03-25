"""Stage 1: Source validation — check raw video metadata before processing."""

from __future__ import annotations

from autoshorts.common.models import VideoMeta, ValidationResult
from autoshorts.validator.checks import (
    check_brands,
    check_dangerous_content,
    check_duration,
    check_license,
)


class SourceValidator:
    """Validates source video metadata for copyright and safety issues."""

    def check_metadata(self, meta: VideoMeta) -> ValidationResult:
        """Run all source-level checks and produce a ValidationResult.

        Score system:
          - duration fail: +100
          - brand detected: +50
          - dangerous content: +100
          - unknown license: +10
          - CC license: -20
        passed = score < 31
        """
        score = 0
        reasons: list[str] = []

        # Duration check
        dur_passed, dur_reasons = check_duration(meta)
        if not dur_passed:
            score += 100
            reasons.extend(dur_reasons)

        # Brand check
        brand_passed, brand_reasons = check_brands(meta)
        if not brand_passed:
            score += 50
            reasons.extend(brand_reasons)

        # Dangerous content check
        danger_passed, danger_reasons = check_dangerous_content(meta)
        if not danger_passed:
            score += 100
            reasons.extend(danger_reasons)

        # License check
        lic_passed, lic_reasons = check_license(meta)
        if not lic_passed:
            score += 10
            reasons.extend(lic_reasons)
        else:
            # License passed — check if it's CC for bonus
            license_info = meta.license_info.lower().strip()
            if license_info and "cc" in license_info:
                score -= 20

        # Clamp score to 0 minimum
        score = max(0, score)

        passed = score < 31

        return ValidationResult(
            video_id=meta.id,
            stage="source",
            passed=passed,
            score=score,
            reasons=reasons,
        )
