"""Tests for platform adapter implementations (Douyin, Bilibili, Kuaishou, Xiaohongshu)."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoshorts.collector.base import CollectResult
from autoshorts.collector.bilibili import BilibiliAdapter, _parse_duration
from autoshorts.collector.douyin import DouyinAdapter
from autoshorts.collector.kuaishou import KuaishouAdapter
from autoshorts.collector.xiaohongshu import XiaohongshuAdapter


# --- Platform name tests ---


class TestPlatformNames:
    def test_douyin_platform_name(self):
        assert DouyinAdapter().platform_name == "douyin"

    def test_bilibili_platform_name(self):
        assert BilibiliAdapter().platform_name == "bilibili"

    def test_kuaishou_platform_name(self):
        assert KuaishouAdapter().platform_name == "kuaishou"

    def test_xiaohongshu_platform_name(self):
        assert XiaohongshuAdapter().platform_name == "xiaohongshu"


# --- BaseCollector interface compliance ---


class TestInterfaceCompliance:
    """Verify all adapters properly implement PlatformAdapter ABC."""

    @pytest.mark.parametrize(
        "adapter_cls",
        [DouyinAdapter, BilibiliAdapter, KuaishouAdapter, XiaohongshuAdapter],
    )
    def test_has_search_method(self, adapter_cls):
        adapter = adapter_cls()
        assert hasattr(adapter, "search")
        assert asyncio.iscoroutinefunction(adapter.search)

    @pytest.mark.parametrize(
        "adapter_cls",
        [DouyinAdapter, BilibiliAdapter, KuaishouAdapter, XiaohongshuAdapter],
    )
    def test_has_download_method(self, adapter_cls):
        adapter = adapter_cls()
        assert hasattr(adapter, "download")
        assert asyncio.iscoroutinefunction(adapter.download)


# --- Bilibili duration parser ---


class TestParseDuration:
    def test_mm_ss(self):
        assert _parse_duration("03:45") == 225.0

    def test_hh_mm_ss(self):
        assert _parse_duration("1:23:45") == 5025.0

    def test_invalid(self):
        assert _parse_duration("invalid") == 0.0

    def test_empty(self):
        assert _parse_duration("") == 0.0

    def test_with_whitespace(self):
        assert _parse_duration("  02:30  ") == 150.0


# --- Download tests with mocked yt-dlp ---


def _make_result(platform: str, video_id: str = "test123") -> CollectResult:
    return CollectResult(
        video_id=video_id,
        platform=platform,
        source_url=f"https://www.{platform}.com/video/{video_id}",
        title=f"Test {platform} video",
        author="testuser",
        duration_seconds=0.0,
        video_path=None,
    )


def _mock_yt_dlp(duration: float = 30.0):
    """Create a mock yt_dlp module."""
    mock_module = MagicMock()
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {"duration": duration}
    mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__exit__ = MagicMock(return_value=False)
    mock_module.YoutubeDL.return_value = mock_ydl_instance
    return mock_module


class TestDouyinDownload:
    @pytest.mark.asyncio
    async def test_download_success(self, tmp_path: Path):
        adapter = DouyinAdapter()
        result = _make_result("douyin")

        import hashlib
        safe_id = hashlib.md5(b"test123").hexdigest()[:12]
        expected_file = tmp_path / f"douyin_{safe_id}.mp4"
        expected_file.write_bytes(b"fake video data")

        with patch.dict("sys.modules", {"yt_dlp": _mock_yt_dlp(30.5)}):
            path = await adapter.download(result, tmp_path)

        assert path == expected_file
        assert result.duration_seconds == 30.5
        assert result.video_path == expected_file

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, tmp_path: Path):
        adapter = DouyinAdapter()
        result = _make_result("douyin")

        with patch.dict("sys.modules", {"yt_dlp": _mock_yt_dlp(10)}):
            with pytest.raises(FileNotFoundError):
                await adapter.download(result, tmp_path)


class TestBilibiliDownload:
    @pytest.mark.asyncio
    async def test_download_success(self, tmp_path: Path):
        adapter = BilibiliAdapter()
        result = _make_result("bilibili", "BV1xx411c7mD")

        import hashlib
        safe_id = hashlib.md5(b"BV1xx411c7mD").hexdigest()[:12]
        expected_file = tmp_path / f"bilibili_{safe_id}.mp4"
        expected_file.write_bytes(b"fake video data")

        with patch.dict("sys.modules", {"yt_dlp": _mock_yt_dlp(120)}):
            path = await adapter.download(result, tmp_path)

        assert path == expected_file
        assert result.duration_seconds == 120.0


class TestKuaishouDownload:
    @pytest.mark.asyncio
    async def test_download_success(self, tmp_path: Path):
        adapter = KuaishouAdapter()
        result = _make_result("kuaishou")

        import hashlib
        safe_id = hashlib.md5(b"test123").hexdigest()[:12]
        expected_file = tmp_path / f"kuaishou_{safe_id}.mp4"
        expected_file.write_bytes(b"fake video data")

        with patch.dict("sys.modules", {"yt_dlp": _mock_yt_dlp(45)}):
            path = await adapter.download(result, tmp_path)

        assert path == expected_file
        assert result.duration_seconds == 45.0


class TestXiaohongshuDownload:
    @pytest.mark.asyncio
    async def test_download_success(self, tmp_path: Path):
        adapter = XiaohongshuAdapter()
        result = _make_result("xiaohongshu")

        import hashlib
        safe_id = hashlib.md5(b"test123").hexdigest()[:12]
        expected_file = tmp_path / f"xhs_{safe_id}.mp4"
        expected_file.write_bytes(b"fake video data")

        with patch.dict("sys.modules", {"yt_dlp": _mock_yt_dlp(60)}):
            path = await adapter.download(result, tmp_path)

        assert path == expected_file
        assert result.duration_seconds == 60.0


# --- Search tests with mocked Playwright ---


def _mock_playwright_card(href: str, title: str, author: str):
    """Create a mock Playwright element for a video card."""
    card = AsyncMock()
    card.get_attribute = AsyncMock(return_value=href)

    title_el = AsyncMock()
    title_el.inner_text = AsyncMock(return_value=title)
    title_el.get_attribute = AsyncMock(return_value=title)

    author_el = AsyncMock()
    author_el.inner_text = AsyncMock(return_value=author)

    async def mock_query_selector(selector: str):
        if "title" in selector:
            return title_el
        if "author" in selector or "name" in selector or "nickname" in selector or "up-name" in selector:
            return author_el
        if "duration" in selector or "time" in selector:
            dur_el = AsyncMock()
            dur_el.inner_text = AsyncMock(return_value="01:30")
            return dur_el
        if "play" in selector or "video" in selector:
            return AsyncMock()
        return None

    card.query_selector = AsyncMock(side_effect=mock_query_selector)
    return card


def _mock_playwright_context(cards):
    """Set up full Playwright mock chain returning given cards."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=cards)

    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)

    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()

    pw = AsyncMock()
    pw.chromium.launch = AsyncMock(return_value=browser)

    pw_manager = AsyncMock()
    pw_manager.__aenter__ = AsyncMock(return_value=pw)
    pw_manager.__aexit__ = AsyncMock(return_value=False)

    return pw_manager


class TestDouyinSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        adapter = DouyinAdapter()
        cards = [
            _mock_playwright_card(
                "https://www.douyin.com/video/123456", "可爱猫咪", "猫咪频道"
            ),
            _mock_playwright_card(
                "/video/789012", "萌狗日常", "狗狗频道"
            ),
        ]
        pw_mock = _mock_playwright_context(cards)

        with patch("playwright.async_api.async_playwright", return_value=pw_mock):
            results = await adapter.search(["可爱动物"], limit=5)

        assert len(results) == 2
        assert results[0].platform == "douyin"
        assert results[0].video_id == "123456"
        assert results[0].source_url == "https://www.douyin.com/video/123456"
        assert results[1].video_id == "789012"

    @pytest.mark.asyncio
    async def test_search_empty(self):
        adapter = DouyinAdapter()
        pw_mock = _mock_playwright_context([])

        with patch("playwright.async_api.async_playwright", return_value=pw_mock):
            results = await adapter.search(["nonexistent"], limit=5)

        assert results == []


class TestBilibiliSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        adapter = BilibiliAdapter()
        cards = [
            _mock_playwright_card(
                "//www.bilibili.com/video/BV1abc123/", "可爱猫咪合集", "UP主一号"
            ),
        ]
        pw_mock = _mock_playwright_context(cards)

        with patch("playwright.async_api.async_playwright", return_value=pw_mock):
            results = await adapter.search(["猫咪"], limit=5)

        assert len(results) == 1
        assert results[0].platform == "bilibili"
        assert results[0].video_id == "BV1abc123"


class TestKuaishouSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        adapter = KuaishouAdapter()
        cards = [
            _mock_playwright_card(
                "https://www.kuaishou.com/short-video/abc123xyz", "可爱狗狗", "快手用户"
            ),
        ]
        pw_mock = _mock_playwright_context(cards)

        with patch("playwright.async_api.async_playwright", return_value=pw_mock):
            results = await adapter.search(["狗狗"], limit=5)

        assert len(results) == 1
        assert results[0].platform == "kuaishou"
        assert results[0].video_id == "abc123xyz"


class TestXiaohongshuSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        adapter = XiaohongshuAdapter()
        cards = [
            _mock_playwright_card(
                "https://www.xiaohongshu.com/explore/note123", "萌宠日记", "小红书用户"
            ),
        ]
        pw_mock = _mock_playwright_context(cards)

        with patch("playwright.async_api.async_playwright", return_value=pw_mock):
            results = await adapter.search(["萌宠"], limit=5)

        assert len(results) == 1
        assert results[0].platform == "xiaohongshu"
        assert results[0].video_id == "note123"
