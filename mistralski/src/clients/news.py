"""RSS news fetcher for game event inspiration."""

import asyncio
import contextlib
from datetime import datetime

import feedparser
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class NewsItem(BaseModel):
    """A parsed news article from RSS."""

    title: str
    description: str = ""
    link: str = ""
    published: datetime | None = None
    source: str = ""


class NewsClient:
    """Fetches and parses RSS feeds for Game Master event generation."""

    def __init__(self, feeds: list[dict[str, str]] | None = None) -> None:
        self._feeds = feeds or [
            {"name": "France Info", "url": "https://www.francetvinfo.fr/titres.rss"},
            {"name": "Le Monde", "url": "https://www.lemonde.fr/rss/une.xml"},
        ]

    async def fetch_latest(self, max_per_feed: int = 5) -> list[NewsItem]:
        """Fetch latest articles from all configured feeds.

        Args:
            max_per_feed: Max articles per feed.

        Returns:
            List of parsed news items.
        """
        tasks = [asyncio.to_thread(self._parse_feed, feed, max_per_feed) for feed in self._feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[NewsItem] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("rss_fetch_failed", error=str(result))
            else:
                items.extend(result)
        return items

    def _parse_feed(self, feed: dict[str, str], max_items: int) -> list[NewsItem]:
        """Parse a single RSS feed (blocking, run in thread)."""
        parsed = feedparser.parse(feed["url"])
        items: list[NewsItem] = []

        for entry in parsed.entries[:max_items]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                with contextlib.suppress(TypeError, ValueError):
                    pub_date = datetime(*entry.published_parsed[:6])

            items.append(
                NewsItem(
                    title=entry.get("title", ""),
                    description=entry.get("summary", ""),
                    link=entry.get("link", ""),
                    published=pub_date,
                    source=feed["name"],
                )
            )
        return items

    async def health_check(self) -> bool:
        """Check if at least one RSS feed is reachable."""
        try:
            items = await self.fetch_latest(max_per_feed=1)
            return len(items) > 0
        except Exception:
            return False
