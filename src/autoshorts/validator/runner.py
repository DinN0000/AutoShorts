"""Validator runner — orchestrates the 3-stage validation pipeline."""

from __future__ import annotations

from pathlib import Path

from autoshorts.common.models import VideoMeta, ValidationResult
from autoshorts.validator.stage1 import SourceValidator


def validate_source(input_dir: str | Path) -> list[ValidationResult]:
    """Run Stage 1 validation on all video metadata files in a directory.

    Looks for *.json files in input_dir and validates each one.
    Returns a list of ValidationResult objects.
    """
    input_path = Path(input_dir)
    validator = SourceValidator()
    results: list[ValidationResult] = []

    for meta_file in sorted(input_path.glob("*.json")):
        try:
            meta = VideoMeta.load(meta_file)
            result = validator.check_metadata(meta)
            results.append(result)
        except Exception:
            # Skip files that can't be parsed as VideoMeta
            continue

    return results


def generate_rejection_stats(results: list[ValidationResult]) -> dict:
    """Generate summary statistics from a list of validation results.

    Returns a dict with:
      - total: total number of results
      - passed: number that passed
      - rejected: number that failed
      - pass_rate: percentage passed
      - common_reasons: dict of reason prefix -> count
    """
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    rejected = total - passed

    reason_counts: dict[str, int] = {}
    for r in results:
        for reason in r.reasons:
            # Use the part before ':' as the category
            key = reason.split(":")[0].strip()
            reason_counts[key] = reason_counts.get(key, 0) + 1

    return {
        "total": total,
        "passed": passed,
        "rejected": rejected,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0.0,
        "common_reasons": reason_counts,
    }
