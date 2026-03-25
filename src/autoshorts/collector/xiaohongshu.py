"""Xiaohongshu (Little Red Book) platform adapter using Playwright + yt-dlp."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from .base import CollectResult, PlatformAdapter

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword={query}&type=video"


class XiaohongshuAdapter(PlatformAdapter):
    """Adapter for collecting videos from Xiaohongshu using Playwright search + yt-dlp download."""

    @property
    def platform_name(self) -> str:
        return "xiaohongshu"

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

                for _ in range(min(3, (limit // 5) + 1)):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await page.wait_for_timeout(1500)

                # Xiaohongshu note cards (videos have a play icon overlay)
                cards = await page.query_selector_all(
                    'a[href*="/explore/"], section[class*="note-item"], div[class*="note-card"]'
                )

                for card in cards[:limit]:
                    try:
                        href = await card.get_attribute("href")
                        if not href:
                            link = await card.query_selector('a[href*="/explore/"]')
                            if link:
                                href = await link.get_attribute("href")
                        if not href or "/explore/" not in href:
                            continue

                        if href.startswith("/"):
                            href = f"https://www.xiaohongshu.com{href}"

                        video_id = href.split("/explore/")[-1].split("?")[0].strip("/")
                        if not video_id:
                            continue

                        title_el = await card.query_selector(
                            'span[class*="title"], a[class*="title"], div[class*="desc"]'
                        )
                        title = (await title_el.inner_text()).strip() if title_el else f"xhs_{video_id}"

                        author_el = await card.query_selector(
                            'span[class*="name"], span[class*="author"], a[class*="author"]'
                        )
                        author = (await author_el.inner_text()).strip() if author_el else "unknown"

                        # Check for video indicator (play icon, video tag)
                        video_indicator = await card.query_selector(
                            'svg[class*="play"], span[class*="play"], div[class*="video"]'
                        )

                        results.append(
                            CollectResult(
                                video_id=video_id,
                                platform="xiaohongshu",
                                source_url=href,
                                title=title,
                                author=author,
                                duration_seconds=0.0,
                                video_path=None,
                                metadata={
                                    "search_query": query,
                                    "has_video_indicator": video_indicator is not None,
                                },
                            )
                        )
                    except Exception:
                        logger.debug("Failed to parse Xiaohongshu card", exc_info=True)
                        continue

            except Exception:
                logger.warning("Xiaohongshu search failed for query: %s", query, exc_info=True)
            finally:
                await browser.close()

        logger.info("Xiaohongshu search found %d results for '%s'", len(results), query)
        return results[:limit]

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        import yt_dlp

        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = hashlib.md5(result.video_id.encode()).hexdigest()[:12]
        output_template = str(output_dir / f"xhs_{safe_id}.%(ext)s")

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
                "Referer": "https://www.xiaohongshu.com/",
            },
        }

        def _download() -> dict:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(result.source_url, download=True)

        info = await asyncio.to_thread(_download)

        if info and info.get("duration"):
            result.duration_seconds = float(info["duration"])

        for f in output_dir.iterdir():
            if f.stem == f"xhs_{safe_id}" and f.suffix in (".mp4", ".webm", ".mkv"):
                result.video_path = f
                logger.info("Downloaded Xiaohongshu video: %s", f.name)
                return f

        raise FileNotFoundError(f"Download completed but file not found for {result.video_id}")
