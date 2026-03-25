"""Claude Vision video frame analysis for copyright validation."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_frames(video_path: str | Path, interval_sec: int = 10) -> list[bytes]:
    """Extract frames from video at fixed intervals using OpenCV.

    Args:
        video_path: Path to video file.
        interval_sec: Seconds between frame captures.

    Returns:
        List of JPEG-encoded frame bytes.
    """
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python not installed, skipping frame extraction")
        return []

    video_path = str(video_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        return []

    frame_interval = int(fps * interval_sec)
    frames: list[bytes] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            # Resize to max 512px width to reduce API cost
            h, w = frame.shape[:2]
            if w > 512:
                scale = 512 / w
                frame = cv2.resize(frame, (512, int(h * scale)))
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frames.append(buf.tobytes())
        frame_idx += 1

    cap.release()
    logger.info("Extracted %d frames from %s", len(frames), video_path)
    return frames


def analyze_frames_with_vision(
    frames: list[bytes],
    api_key: str | None = None,
) -> dict:
    """Send frames to Claude Vision API for copyright risk analysis.

    Args:
        frames: List of JPEG-encoded frame bytes.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        Dict with keys: vision_score (0-100), issues (list[str]), summary (str).
    """
    if not frames:
        return {"vision_score": 0, "issues": [], "summary": "No frames to analyze"}

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        logger.warning("No ANTHROPIC_API_KEY set, skipping vision analysis")
        return {"vision_score": 0, "issues": [], "summary": "API key not configured"}

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic SDK not installed, skipping vision analysis")
        return {"vision_score": 0, "issues": [], "summary": "SDK not installed"}

    # Limit to max 6 frames to control cost
    if len(frames) > 6:
        step = len(frames) / 6
        frames = [frames[int(i * step)] for i in range(6)]

    content: list[dict] = []
    for i, frame_bytes in enumerate(frames):
        b64 = base64.b64encode(frame_bytes).decode("utf-8")
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            }
        )
    content.append(
        {
            "type": "text",
            "text": (
                "You are a copyright risk assessor for short-form animal videos. "
                "Analyze these video frames and evaluate copyright risk.\n\n"
                "Check for:\n"
                "1. Visible logos, watermarks, or brand text\n"
                "2. Recognizable copyrighted characters (cartoon, movie, game)\n"
                "3. TV broadcast overlays, channel bugs, or news tickers\n"
                "4. Professional studio production indicators\n"
                "5. Text overlays from other creators (TikTok usernames, etc.)\n\n"
                "Respond in EXACTLY this JSON format, nothing else:\n"
                '{"vision_score": <0-100 integer, higher=more risk>, '
                '"issues": [<list of specific issues found>], '
                '"summary": "<one sentence summary>"}'
            ),
        }
    )

    client = anthropic.Anthropic(api_key=key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": content}],
        )
        import json

        text = response.content[0].text.strip()
        # Handle possible markdown code block wrapping
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        # Validate expected keys
        return {
            "vision_score": int(result.get("vision_score", 0)),
            "issues": list(result.get("issues", [])),
            "summary": str(result.get("summary", "")),
        }
    except Exception as e:
        logger.error("Vision API call failed: %s", e)
        return {"vision_score": 0, "issues": [], "summary": f"API error: {e}"}


def analyze_video(
    video_path: str | Path,
    interval_sec: int = 10,
    api_key: str | None = None,
) -> dict:
    """Full pipeline: extract frames and analyze with Vision.

    Returns dict with vision_score, issues, summary, frame_count.
    """
    frames = extract_frames(video_path, interval_sec)
    result = analyze_frames_with_vision(frames, api_key)
    result["frame_count"] = len(frames)
    return result
