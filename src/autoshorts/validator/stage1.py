"""Stage 1: Source validation — check raw video metadata before processing."""

from __future__ import annotations

import logging

from autoshorts.common.models import VideoMeta, ValidationResult
from autoshorts.validator.checks import (
    check_brands,
    check_dangerous_content,
    check_duration,
    check_license,
)
from autoshorts.validator.youtube_similarity import (
    SIMILARITY_THRESHOLD,
    check_youtube_similarity,
)

logger = logging.getLogger(__name__)


class SourceValidator:
    """Validates source video metadata for copyright and safety issues."""

    def __init__(self, youtube_api_key: str | None = None):
        self._youtube_api_key = youtube_api_key

    def check_metadata(
        self,
        meta: VideoMeta,
        thumbnail_bytes: bytes | None = None,
    ) -> ValidationResult:
        """Run all source-level checks and produce a ValidationResult.

        Score system:
          - youtube_duplicate (>= 75% similarity): +100  ← HARD GATE
          - duration fail: +100
          - brand detected: +50
          - dangerous content: +100
          - unknown license: +10
          - CC license: -20
        passed = score < 31
        """
        score = 0
        reasons: list[str] = []
        details: dict = {}

        # ── HARD GATE: YouTube similarity check ──────────────────────
        is_dup, max_sim, matches = check_youtube_similarity(
            title=meta.title,
            tags=meta.tags,
            thumbnail_bytes=thumbnail_bytes,
            api_key=self._youtube_api_key,
        )
        if is_dup:
            score += 100
            top = matches[0]
            reasons.append(
                f"youtube_duplicate: {max_sim:.1f}% similar to "
                f"'{top.title}' ({top.video_id})"
            )
            details["youtube_similarity"] = {
                "max_similarity": max_sim,
                "threshold": SIMILARITY_THRESHOLD,
                "top_match_id": top.video_id,
                "top_match_title": top.title,
                "text_similarity": top.text_similarity,
                "thumbnail_similarity": top.thumbnail_similarity,
            }
            logger.info(
                "HARD GATE: video '%s' is %.1f%% similar to YouTube '%s' — auto-reject",
                meta.title, max_sim, top.title,
            )

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
            details=details,
        )
