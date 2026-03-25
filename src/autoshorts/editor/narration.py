"""Narration stubs — transcription via Whisper and storyline via Claude."""

from __future__ import annotations


async def transcribe_audio(video_path: str) -> str:
    """Transcribe audio from a video file using Whisper."""
    raise NotImplementedError("Whisper transcription not yet implemented")


async def generate_storyline(original_text: str) -> str:
    """Generate a new storyline from original text using Claude."""
    raise NotImplementedError("Claude storyline generation not yet implemented")
