"""Text-to-speech using edge_tts."""

from __future__ import annotations

import edge_tts

VOICE_MAP: dict[str, str] = {
    "en": "en-US-AriaNeural",
    "ko": "ko-KR-SunHiNeural",
    "ja": "ja-JP-NanamiNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "pt": "pt-BR-FranciscaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ar": "ar-SA-ZariyahNeural",
}


async def generate_tts(text: str, lang: str, output_path: str) -> None:
    """Generate TTS audio using edge_tts and save to output_path."""
    voice = VOICE_MAP.get(lang)
    if voice is None:
        raise ValueError(f"Unsupported language: {lang!r}. Supported: {list(VOICE_MAP)}")

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
