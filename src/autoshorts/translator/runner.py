"""Translator runner — translate, subtitle, and TTS localization."""

from __future__ import annotations

from pathlib import Path

from .subtitle import SrtEntry, generate_srt
from .tts import generate_tts


async def translate_and_localize(
    text: str,
    lang: str,
    output_dir: str,
    entries: list[SrtEntry] | None = None,
) -> dict[str, str]:
    """Translate text, generate subtitles and TTS for a target language.

    Returns a dict with paths to the generated SRT and audio files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Generate subtitles
    if entries is None:
        entries = [SrtEntry.from_seconds(1, 0.0, len(text) * 0.05, text)]
    srt_content = generate_srt(entries)
    srt_path = out / f"subtitles_{lang}.srt"
    srt_path.write_text(srt_content, encoding="utf-8")

    # Generate TTS
    tts_path = out / f"tts_{lang}.mp3"
    await generate_tts(text, lang, str(tts_path))

    return {
        "srt_path": str(srt_path),
        "tts_path": str(tts_path),
    }
