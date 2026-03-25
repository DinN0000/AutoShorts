"""YouTube similarity checker — detect duplicate/similar content on YouTube.

Uses YouTube Data API v3 for search, fuzzywuzzy for text similarity,
and OpenCV for thumbnail comparison. When similarity >= 75%, the video
is flagged for immediate rejection (hard gate).
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from typing import Any

import yaml

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 75  # percent — at or above this triggers hard gate

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_api_key() -> str | None:
    """Load YouTube API key: env var first, then config/secrets.yaml fallback."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key

    secrets_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "secrets.yaml"
    )
    try:
        with open(secrets_path) as f:
            data = yaml.safe_load(f) or {}
        return data.get("youtube", {}).get("api_key")
    except (FileNotFoundError, yaml.YAMLError):
        return None


# ---------------------------------------------------------------------------
# Text similarity (fuzzywuzzy)
# ---------------------------------------------------------------------------

def compute_text_similarity(
    title_a: str,
    tags_a: list[str],
    title_b: str,
    tags_b: list[str],
) -> float:
    """Return 0–100 similarity score between two videos based on title+tags.

    Uses token_set_ratio for titles (handles word-order differences) and
    overlap ratio for tags.
    """
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        logger.warning("fuzzywuzzy not installed — text similarity disabled")
        return 0.0

    # Title similarity (0-100)
    title_score = fuzz.token_set_ratio(title_a.lower(), title_b.lower())

    # Tag overlap
    set_a = {t.lower().strip() for t in tags_a if t.strip()}
    set_b = {t.lower().strip() for t in tags_b if t.strip()}
    if set_a and set_b:
        intersection = set_a & set_b
        union = set_a | set_b
        tag_score = (len(intersection) / len(union)) * 100
    elif not set_a and not set_b:
        tag_score = 0.0  # no tags to compare — neutral
    else:
        tag_score = 0.0

    # Weighted: title 70%, tags 30%
    return title_score * 0.7 + tag_score * 0.3


# ---------------------------------------------------------------------------
# Thumbnail similarity (OpenCV)
# ---------------------------------------------------------------------------

def compute_thumbnail_similarity(img_bytes_a: bytes, img_bytes_b: bytes) -> float:
    """Return 0–100 similarity score between two thumbnail images.

    Uses histogram comparison (correlation method) on HSV color space.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("opencv-python not installed — thumbnail similarity disabled")
        return 0.0

    def _decode(raw: bytes) -> Any:
        arr = np.frombuffer(raw, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    img_a = _decode(img_bytes_a)
    img_b = _decode(img_bytes_b)

    if img_a is None or img_b is None:
        return 0.0

    # Resize to same dimensions for fair comparison
    target_size = (128, 128)
    img_a = cv2.resize(img_a, target_size)
    img_b = cv2.resize(img_b, target_size)

    # Convert to HSV
    hsv_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2HSV)
    hsv_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2HSV)

    # Calculate histograms
    h_bins, s_bins = 50, 60
    hist_size = [h_bins, s_bins]
    ranges = [0, 180, 0, 256]
    channels = [0, 1]

    hist_a = cv2.calcHist([hsv_a], channels, None, hist_size, ranges)
    cv2.normalize(hist_a, hist_a, 0, 1, cv2.NORM_MINMAX)

    hist_b = cv2.calcHist([hsv_b], channels, None, hist_size, ranges)
    cv2.normalize(hist_b, hist_b, 0, 1, cv2.NORM_MINMAX)

    # Compare — HISTCMP_CORREL returns -1..1, we map to 0..100
    correlation = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return max(0.0, correlation) * 100


# ---------------------------------------------------------------------------
# YouTube API search
# ---------------------------------------------------------------------------

@dataclass
class YouTubeMatch:
    """A single YouTube search result with similarity info."""
    video_id: str
    title: str
    tags: list[str]
    thumbnail_url: str
    text_similarity: float
    thumbnail_similarity: float
    combined_similarity: float


def _fetch_thumbnail(url: str) -> bytes | None:
    """Download thumbnail image bytes."""
    try:
        from urllib.request import urlopen, Request
        req = Request(url, headers={"User-Agent": "AutoShorts/0.1"})
        with urlopen(req, timeout=10) as resp:
            return resp.read()
    except Exception:
        logger.debug("Failed to fetch thumbnail: %s", url)
        return None


def search_youtube_similar(
    title: str,
    tags: list[str],
    thumbnail_bytes: bytes | None = None,
    api_key: str | None = None,
    max_results: int = 10,
) -> list[YouTubeMatch]:
    """Search YouTube for videos similar to the given title/tags.

    Returns a list of YouTubeMatch objects sorted by combined_similarity descending.
    """
    if api_key is None:
        api_key = _load_api_key()

    if not api_key:
        logger.warning("No YouTube API key available — similarity search skipped")
        return []

    try:
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("google-api-python-client not installed — YouTube search disabled")
        return []

    # Build search query from title + top tags
    query_parts = [title]
    if tags:
        query_parts.extend(tags[:3])
    query = " ".join(query_parts)

    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        # Search
        search_resp = (
            youtube.search()
            .list(q=query, part="snippet", type="video", maxResults=max_results)
            .execute()
        )

        video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
        if not video_ids:
            return []

        # Get full video details (includes tags)
        videos_resp = (
            youtube.videos()
            .list(id=",".join(video_ids), part="snippet")
            .execute()
        )
    except Exception as e:
        logger.error("YouTube API error: %s", e)
        return []

    matches: list[YouTubeMatch] = []

    for item in videos_resp.get("items", []):
        snippet = item["snippet"]
        yt_title = snippet.get("title", "")
        yt_tags = snippet.get("tags", [])
        yt_thumb_url = (
            snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
            or snippet.get("thumbnails", {}).get("default", {}).get("url", "")
        )

        # Text similarity
        text_sim = compute_text_similarity(title, tags, yt_title, yt_tags)

        # Thumbnail similarity (if we have source thumbnail)
        thumb_sim = 0.0
        if thumbnail_bytes and yt_thumb_url:
            yt_thumb_bytes = _fetch_thumbnail(yt_thumb_url)
            if yt_thumb_bytes:
                thumb_sim = compute_thumbnail_similarity(thumbnail_bytes, yt_thumb_bytes)

        # Combined: text 60%, thumbnail 40% (or 100% text if no thumbnail)
        if thumbnail_bytes:
            combined = text_sim * 0.6 + thumb_sim * 0.4
        else:
            combined = text_sim

        matches.append(
            YouTubeMatch(
                video_id=item["id"],
                title=yt_title,
                tags=yt_tags,
                thumbnail_url=yt_thumb_url,
                text_similarity=round(text_sim, 1),
                thumbnail_similarity=round(thumb_sim, 1),
                combined_similarity=round(combined, 1),
            )
        )

    matches.sort(key=lambda m: m.combined_similarity, reverse=True)
    return matches


# ---------------------------------------------------------------------------
# High-level check
# ---------------------------------------------------------------------------

def check_youtube_similarity(
    title: str,
    tags: list[str],
    thumbnail_bytes: bytes | None = None,
    api_key: str | None = None,
) -> tuple[bool, float, list[YouTubeMatch]]:
    """Check if a video is too similar to existing YouTube content.

    Returns:
        (is_duplicate, max_similarity, matches)
        is_duplicate = True if max_similarity >= SIMILARITY_THRESHOLD
    """
    matches = search_youtube_similar(
        title=title,
        tags=tags,
        thumbnail_bytes=thumbnail_bytes,
        api_key=api_key,
    )

    if not matches:
        return False, 0.0, []

    max_sim = matches[0].combined_similarity
    is_duplicate = max_sim >= SIMILARITY_THRESHOLD

    return is_duplicate, max_sim, matches
