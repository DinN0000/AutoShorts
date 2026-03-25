"""Upload scheduling with timezone-aware primetime detection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


# (country_code, utc_offset_hours, primetime_start_hour, primetime_end_hour)
TIMEZONE_MAP: dict[str, tuple[str, int, int, int]] = {
    "en": ("US", -5, 18, 21),
    "ko": ("KR", 9, 19, 22),
    "ja": ("JP", 9, 19, 22),
    "de": ("DE", 1, 18, 21),
    "fr": ("FR", 1, 18, 21),
    "es": ("ES", 1, 19, 22),
    "pt": ("BR", -3, 19, 22),
    "hi": ("IN", 5, 19, 22),
    "ar": ("SA", 3, 20, 23),
}


def get_optimal_upload_time(
    lang: str, country: Optional[str] = None
) -> datetime:
    """Return an optimal upload datetime at the middle of primetime.

    The returned datetime is in UTC but represents the middle of the
    primetime window for the given language/country.
    """
    if lang not in TIMEZONE_MAP:
        raise ValueError(f"Unsupported language: {lang}")

    country_code, utc_offset, prime_start, prime_end = TIMEZONE_MAP[lang]

    tz = timezone(timedelta(hours=utc_offset))
    now_local = datetime.now(tz)

    # Middle of primetime window
    mid_hour = (prime_start + prime_end) // 2

    # Target today at mid_hour local time
    target_local = now_local.replace(
        hour=mid_hour, minute=30, second=0, microsecond=0
    )

    # If we've already passed that time today, schedule for tomorrow
    if target_local <= now_local:
        target_local += timedelta(days=1)

    return target_local
