"""SRT subtitle generation."""

from __future__ import annotations

from dataclasses import dataclass


def _format_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm."""
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


@dataclass
class SrtEntry:
    index: int
    start: str  # "HH:MM:SS,mmm"
    end: str  # "HH:MM:SS,mmm"
    text: str

    @classmethod
    def from_seconds(
        cls, index: int, start_sec: float, end_sec: float, text: str
    ) -> SrtEntry:
        return cls(
            index=index,
            start=_format_timestamp(start_sec),
            end=_format_timestamp(end_sec),
            text=text,
        )


def generate_srt(entries: list[SrtEntry]) -> str:
    """Generate an SRT subtitle string from a list of entries."""
    blocks: list[str] = []
    for entry in entries:
        block = f"{entry.index}\n{entry.start} --> {entry.end}\n{entry.text}"
        blocks.append(block)
    return "\n\n".join(blocks) + "\n"
