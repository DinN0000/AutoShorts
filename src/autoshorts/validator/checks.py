"""Individual validation check functions."""

from __future__ import annotations

from autoshorts.common.models import VideoMeta

BRAND_KEYWORDS = [
    "nike", "adidas", "gucci", "prada", "louis vuitton", "chanel",
    "coca cola", "pepsi", "mcdonalds", "starbucks", "apple", "samsung",
    "disney", "marvel", "pokemon", "nintendo",
]

DANGEROUS_KEYWORDS = [
    "虐待", "abuse", "fight", "打架", "受伤", "hurt", "cruelty",
]

MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 180


def check_brands(meta: VideoMeta) -> tuple[bool, list[str]]:
    """Check for brand/trademark references in title and tags.

    Returns (passed, reasons). passed=True means NO brands found.
    """
    reasons: list[str] = []
    text = meta.title.lower()
    all_tags = [t.lower() for t in meta.tags]

    for brand in BRAND_KEYWORDS:
        if brand in text or brand in all_tags:
            reasons.append(f"brand_detected: {brand}")

    passed = len(reasons) == 0
    return passed, reasons


def check_dangerous_content(meta: VideoMeta) -> tuple[bool, list[str]]:
    """Check for dangerous/abusive content keywords.

    Returns (passed, reasons). passed=True means NO dangerous content found.
    """
    reasons: list[str] = []
    text = (meta.title + " " + " ".join(meta.tags)).lower()

    for keyword in DANGEROUS_KEYWORDS:
        if keyword in text:
            reasons.append(f"dangerous_content: {keyword}")

    passed = len(reasons) == 0
    return passed, reasons


def check_duration(meta: VideoMeta) -> tuple[bool, list[str]]:
    """Check video duration is within acceptable range.

    Returns (passed, reasons). passed=True means duration is valid.
    """
    reasons: list[str] = []

    if meta.duration_seconds < MIN_DURATION_SECONDS:
        reasons.append(f"too_short: {meta.duration_seconds}s < {MIN_DURATION_SECONDS}s")
    elif meta.duration_seconds > MAX_DURATION_SECONDS:
        reasons.append(f"too_long: {meta.duration_seconds}s > {MAX_DURATION_SECONDS}s")

    passed = len(reasons) == 0
    return passed, reasons


def check_license(meta: VideoMeta) -> tuple[bool, list[str]]:
    """Check video license information.

    Returns (passed, reasons). passed=True means license is acceptable.
    """
    reasons: list[str] = []
    license_info = meta.license_info.lower().strip()

    if not license_info or license_info == "unknown":
        reasons.append("unknown_license")
    elif "cc" in license_info:
        # Creative Commons licenses are good — no issue
        pass
    else:
        reasons.append(f"non_cc_license: {license_info}")

    passed = len(reasons) == 0
    return passed, reasons
