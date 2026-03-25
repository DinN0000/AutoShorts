"""Tests for translator runner module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoshorts.translator.runner import (
    LANGUAGE_NAMES,
    translate_text,
    translate_metadata,
    translate_srt_entries,
)
from autoshorts.translator.subtitle import SrtEntry


def _mock_response(text: str) -> MagicMock:
    """Create a mock Claude API response with the given text."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


class TestTranslateText:
    @patch("autoshorts.translator.runner.anthropic.Anthropic")
    def test_translate_text_returns_translated(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("Hola mundo")

        result = translate_text("Hello world", "es")

        assert result == "Hola mundo"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-haiku-4-5"
        assert "Spanish" in call_kwargs["messages"][0]["content"]

    @patch("autoshorts.translator.runner.anthropic.Anthropic")
    def test_translate_text_strips_whitespace(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("  Bonjour  \n")

        result = translate_text("Hello", "fr")
        assert result == "Bonjour"


class TestTranslateMetadata:
    @patch("autoshorts.translator.runner.anthropic.Anthropic")
    def test_translate_metadata_returns_title_and_desc(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response(
            "Gato lindo\nUn video de un gato muy lindo"
        )

        result = translate_metadata("Cute cat", "A video of a cute cat", "es")

        assert result["title"] == "Gato lindo"
        assert result["description"] == "Un video de un gato muy lindo"

    @patch("autoshorts.translator.runner.anthropic.Anthropic")
    def test_translate_metadata_single_line(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("Gato lindo")

        result = translate_metadata("Cute cat", "", "es")
        assert result["title"] == "Gato lindo"
        assert result["description"] == ""


class TestTranslateSrtEntries:
    @patch("autoshorts.translator.runner.anthropic.Anthropic")
    def test_translates_entries_preserving_timing(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response(
            "Hola mundo\n---\nSegunda linea"
        )

        entries = [
            SrtEntry(index=1, start="00:00:00,000", end="00:00:02,500", text="Hello world"),
            SrtEntry(index=2, start="00:00:03,000", end="00:00:05,000", text="Second line"),
        ]

        result = translate_srt_entries(entries, "es")

        assert len(result) == 2
        assert result[0].text == "Hola mundo"
        assert result[1].text == "Segunda linea"
        # Timing preserved
        assert result[0].start == "00:00:00,000"
        assert result[0].end == "00:00:02,500"
        assert result[1].start == "00:00:03,000"

    @patch("autoshorts.translator.runner.anthropic.Anthropic")
    def test_empty_entries_returns_empty(self, mock_cls):
        result = translate_srt_entries([], "es")
        assert result == []
        mock_cls.assert_not_called()


class TestLanguageNames:
    def test_all_nine_languages_present(self):
        expected = {"en", "ko", "ja", "de", "fr", "es", "pt", "hi", "ar"}
        assert set(LANGUAGE_NAMES.keys()) == expected
