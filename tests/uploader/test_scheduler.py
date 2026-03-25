"""Tests for upload scheduler."""

from autoshorts.uploader.scheduler import TIMEZONE_MAP, get_optimal_upload_time


def test_us_primetime():
    """US primetime should be between 17-21 UTC-5 (local hour)."""
    dt = get_optimal_upload_time("en")
    # Convert to US Eastern local hour
    local_hour = dt.hour
    assert 17 <= local_hour <= 21, f"US primetime hour {local_hour} not in 17-21"


def test_japan_primetime():
    """Japan primetime should be between 18-22 JST (local hour)."""
    dt = get_optimal_upload_time("ja")
    local_hour = dt.hour
    assert 18 <= local_hour <= 22, f"Japan primetime hour {local_hour} not in 18-22"


def test_timezone_map_has_all_languages():
    """TIMEZONE_MAP must contain entries for all supported languages."""
    expected = {"en", "ko", "ja", "de", "fr", "es", "pt", "hi", "ar"}
    assert set(TIMEZONE_MAP.keys()) == expected
