"""Bilibili platform adapter using Playwright + yt-dlp."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from .base import CollectResult, PlatformAdapter

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://search.bilibili.com/video?keyword={query}&order=totalrank"


class BilibiliAdapter(PlatformAdapter):
    """Adapter for collecting videos from Bilibili using Playwright search + yt-dlp download."""

    @property
    def platform_name(self) -> str:
        return "bilibili"

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

                # Bilibili search result cards
                cards = await page.query_selector_all(
                    'div.video-list-item, div[class*="video-card"], a[href*="bilibili.com/video/"]'
                )

                for card in cards[:limit]:
                    try:
                        link = card
                        href = await card.get_attribute("href")
                        if not href:
                            link = await card.query_selector(
                                'a[href*="/video/"], a[href*="bilibili.com"]'
                            )
                            if link:
                                href = await link.get_attribute("href")
                        if not href or "/video/" not in href:
                            continue

                        if href.startswith("//"):
                            href = f"https:{href}"
                        elif href.startswith("/"):
                            href = f"https://www.bilibili.com{href}"

                        # Extract BV ID
                        video_id = ""
                        for segment in href.split("/"):
                            if segment.startswith("BV"):
                                video_id = segment.split("?")[0]
                                break
                        if not video_id:
                            continue

                        title_el = await card.query_selector(
                            'h3, a[title], span[class*="title"], div[class*="title"]'
                        )
                        title = ""
                        if title_el:
                            title = (await title_el.get_attribute("title")) or ""
                            if not title:
                                title = (await title_el.inner_text()).strip()
                        title = title or f"bilibili_{video_id}"

                        author_el = await card.query_selector(
                            'span[class*="up-name"], span[class*="author"]'
                        )
                        author = (await author_el.inner_text()).strip() if author_el else "unknown"

                        duration_el = await card.query_selector(
                            'span[class*="duration"], span[class*="time"]'
                        )
                        duration = 0.0
                        if duration_el:
                            dur_text = (await duration_el.inner_text()).strip()
                            duration = _parse_duration(dur_text)

                        results.append(
                            CollectResult(
                                video_id=video_id,
                                platform="bilibili",
                                source_url=href,
                                title=title,
                                author=author,
                                duration_seconds=duration,
                                video_path=None,
                                metadata={"search_query": query},
                            )
                        )
                    except Exception:
                        logger.debug("Failed to parse Bilibili card", exc_info=True)
                        continue

            except Exception:
                logger.warning("Bilibili search failed for query: %s", query, exc_info=True)
            finally:
                await browser.close()

        logger.info("Bilibili search found %d results for '%s'", len(results), query)
        return results[:limit]

    async def download(self, result: CollectResult, output_dir: Path) -> Path:
        import yt_dlp

        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = hashlib.md5(result.video_id.encode()).hexdigest()[:12]
        output_template = str(output_dir / f"bilibili_{safe_id}.%(ext)s")

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
                "Referer": "https://www.bilibili.com/",
            },
        }

        def _download() -> dict:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(result.source_url, download=True)

        info = await asyncio.to_thread(_download)

        if info and info.get("duration"):
            result.duration_seconds = float(info["duration"])

        for f in output_dir.iterdir():
            if f.stem == f"bilibili_{safe_id}" and f.suffix in (".mp4", ".webm", ".mkv", ".flv"):
                result.video_path = f
                logger.info("Downloaded Bilibili video: %s", f.name)
                return f

        raise FileNotFoundError(f"Download completed but file not found for {result.video_id}")


def _parse_duration(text: str) -> float:
    """Parse duration string like '03:45' or '1:23:45' to seconds."""
    try:
        parts = text.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0.0
