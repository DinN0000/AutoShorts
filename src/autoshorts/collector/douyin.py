"""Douyin (TikTok China) platform adapter using Playwright + yt-dlp."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

from .base import CollectResult, PlatformAdapter

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.douyin.com/search/{query}?type=video"


class DouyinAdapter(PlatformAdapter):
    """Adapter for collecting videos from Douyin using Playwright search + yt-dlp download."""

    @property
    def platform_name(self) -> str:
        return "douyin"

    async def search(self, keywords: list[str], limit: int) -> list[CollectResult]:
        from playwright.async_api import async_playwright

        results: list[CollectResult] = []
        query = " ".join(keywords)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            page = await context.new_page()

            try:
                url = _SEARCH_URL.format(query=query)
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # Scroll to load more results
                for _ in range(min(3, (limit // 5) + 1)):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await page.wait_for_timeout(1500)

                # Extract video cards from search results
                cards = await page.query_selector_all(
                    'a[href*="/video/"], div[data-e2e="search-card"]'
                )

                for card in cards[:limit]:
                    try:
                        href = await card.get_attribute("href")
                        if not href:
                            link = await card.query_selector('a[href*="/video/"]')
                            if link:
                                href = await link.get_attribute("href")
                        if not href or "/video/" not in href:
                            continue

                        if href.startswith("/"):
                            href = f"https://www.douyin.com{href}"

                        video_id = href.split("/video/")[-1].split("?")[0].strip("/")
                        if not video_id:
                            continue

                        title_el = await card.query_selector(
                            'p, span[class*="title"], div[class*="title"]'
                        )
                        title = (await title_el.inner_text()).strip() if title_el else f"douyin_{video_id}"

                        author_el = await card.query_selector(
                            'span[class*="author"], span[class*="nickname"]'
                        )
                        author = (await author_el.inner_text()).strip() if author_el else "unknown"

                        results.append(
                            CollectResult(
                                video_id=video_id,
                                platform="douyin",
                                source_url=href,
                                title=title,
                                author=author,
                                duration_seconds=0.0,
                                video_path=None,
                                metadata={"search_query": query},
                            )
                        )
                    except Exception:
                        logger.debug("Failed to parse Douyin card", exc_info=True)
                        continue

            except Exception:
                logger.warning("Douyin search failed for query: %s", query, exc_info=True)
            finally:
                await browser.close()

        logger.info("Douyin search found %d results for '%s'", len(results), query)
        return results[:limit]

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        import yt_dlp

        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = hashlib.md5(result.video_id.encode()).hexdigest()[:12]
        output_template = str(output_dir / f"douyin_{safe_id}.%(ext)s")

        ydl_opts = {
            "outtmpl": output_template,
            "format": "best[height<=1080]",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.douyin.com/",
            },
        }

        def _download() -> dict:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(result.source_url, download=True)

        info = await asyncio.to_thread(_download)

        if info and info.get("duration"):
            result.duration_seconds = float(info["duration"])

        # Find the downloaded file
        for f in output_dir.iterdir():
            if f.stem == f"douyin_{safe_id}" and f.suffix in (".mp4", ".webm", ".mkv"):
                result.video_path = f
                logger.info("Downloaded Douyin video: %s", f.name)
                return f

        raise FileNotFoundError(f"Download completed but file not found for {result.video_id}")
