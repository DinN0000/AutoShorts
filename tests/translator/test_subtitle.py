"""Tests for translator subtitle module."""

from autoshorts.translator.subtitle import SrtEntry, generate_srt, _format_timestamp


def test_generate_srt():
    entries = [
        SrtEntry(index=1, start="00:00:00,000", end="00:00:02,500", text="Hello world"),
        SrtEntry(index=2, start="00:00:03,000", end="00:00:05,000", text="Second line"),
    ]
    result = generate_srt(entries)
    assert "1\n00:00:00,000 --> 00:00:02,500\nHello world" in result
    assert "2\n00:00:03,000 --> 00:00:05,000\nSecond line" in result
    # Entries separated by blank line
    assert "\n\n" in result


def test_srt_entry_from_seconds():
    entry1 = SrtEntry.from_seconds(1, 0.0, 2.5, "Hello")
    assert entry1.start == "00:00:00,000"
    assert entry1.end == "00:00:02,500"

    entry2 = SrtEntry.from_seconds(2, 3.5, 10.0, "World")
    assert entry2.start == "00:00:03,500"
    assert entry2.end == "00:00:10,000"
