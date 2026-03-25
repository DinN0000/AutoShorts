"""Translator runner — translate, subtitle, and TTS localization."""

from __future__ import annotations

import os
from pathlib import Path

import anthropic

from .subtitle import SrtEntry, generate_srt
from .tts import generate_tts

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "hi": "Hindi",
    "ar": "Arabic",
}


def translate_text(text: str, target_lang: str) -> str:
    """Translate text to the target language using Claude API.

    Uses ANTHROPIC_API_KEY environment variable for authentication.
    """
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system="You are a professional translator for short-form animal video content. Translate naturally and concisely. Output ONLY the translated text, nothing else.",
        messages=[
            {
                "role": "user",
                "content": f"Translate the following text to {lang_name}:\n\n{text}",
            }
        ],
    )
    translated = next(
        (block.text for block in response.content if block.type == "text"), ""
    )
    return translated.strip()


def translate_metadata(
    title: str, description: str, target_lang: str
) -> dict[str, str]:
    """Translate video title and description for a target language."""
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=(
            "You are a professional translator for short-form animal video content. "
            "Translate the title and description naturally. "
            "Output exactly two lines: first line is the translated title, "
            "second line is the translated description. Nothing else."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Translate to {lang_name}:\n\n"
                    f"Title: {title}\n"
                    f"Description: {description}"
                ),
            }
        ],
    )
    result = next(
        (block.text for block in response.content if block.type == "text"), ""
    ).strip()

    lines = result.split("\n", 1)
    translated_title = lines[0].strip()
    translated_description = lines[1].strip() if len(lines) > 1 else ""

    return {"title": translated_title, "description": translated_description}


def translate_srt_entries(
    entries: list[SrtEntry], target_lang: str
) -> list[SrtEntry]:
    """Translate SRT subtitle entries to the target language."""
    if not entries:
        return []

    texts = [e.text for e in entries]
    combined = "\n---\n".join(texts)

    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=(
            "You are a professional subtitle translator for short-form animal videos. "
            "Translate each subtitle segment naturally. "
            "Keep the same number of segments separated by '---'. "
            "Output ONLY the translated segments, nothing else."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Translate to {lang_name}:\n\n{combined}",
            }
        ],
    )
    result = next(
        (block.text for block in response.content if block.type == "text"), ""
    ).strip()

    translated_texts = [t.strip() for t in result.split("---")]

    translated_entries = []
    for i, entry in enumerate(entries):
        t_text = translated_texts[i] if i < len(translated_texts) else entry.text
        translated_entries.append(
            SrtEntry(
                index=entry.index,
                start=entry.start,
                end=entry.end,
                text=t_text,
            )
        )
    return translated_entries


async def translate_and_localize(
    text: str,
    lang: str,
    output_dir: str,
    entries: list[SrtEntry] | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, str]:
    """Translate text, generate subtitles and TTS for a target language.

    Returns a dict with paths to the generated SRT, audio, and metadata files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Translate main text
    translated_text = translate_text(text, lang)

    # Translate and generate subtitles
    if entries is not None:
        translated_entries = translate_srt_entries(entries, lang)
    else:
        translated_entries = [
            SrtEntry.from_seconds(1, 0.0, len(translated_text) * 0.05, translated_text)
        ]
    srt_content = generate_srt(translated_entries)
    srt_path = out / f"subtitles_{lang}.srt"
    srt_path.write_text(srt_content, encoding="utf-8")

    # Generate TTS from translated text
    tts_path = out / f"tts_{lang}.mp3"
    await generate_tts(translated_text, lang, str(tts_path))

    result: dict[str, str] = {
        "srt_path": str(srt_path),
        "tts_path": str(tts_path),
        "translated_text": translated_text,
    }

    # Translate metadata if provided
    if title or description:
        meta = translate_metadata(title or "", description or "", lang)
        meta_path = out / f"metadata_{lang}.txt"
        meta_path.write_text(
            f"{meta['title']}\n{meta['description']}", encoding="utf-8"
        )
        result["metadata_path"] = str(meta_path)
        result["translated_title"] = meta["title"]
        result["translated_description"] = meta["description"]

    return result
