"""HackerNews signal collector — fetches top and new stories via the Firebase API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from zeitgeist.models import Signal
from zeitgeist.sources.base import SignalCollector

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"
MAX_STORIES = 30
CONCURRENT_LIMIT = 10


class HackerNewsCollector(SignalCollector):
    """Collect signals from Hacker News top and new stories."""

    name = "hackernews"

    async def collect(self) -> list[Signal]:
        signals: list[Signal] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            top_ids, new_ids = await asyncio.gather(
                self._fetch_ids(client, "topstories"),
                self._fetch_ids(client, "newstories"),
            )

            story_ids = list(dict.fromkeys(top_ids[:MAX_STORIES] + new_ids[:MAX_STORIES]))
            sem = asyncio.Semaphore(CONCURRENT_LIMIT)

            async def _fetch_one(sid: int) -> Signal | None:
                async with sem:
                    return await self._fetch_story(client, sid)

            results = await asyncio.gather(*[_fetch_one(sid) for sid in story_ids])
            signals = [s for s in results if s is not None]

        logger.info("HackerNews collected %d signals", len(signals))
        return signals

    async def _fetch_ids(self, client: httpx.AsyncClient, endpoint: str) -> list[int]:
        try:
            resp = await client.get(f"{HN_API}/{endpoint}.json")
            resp.raise_for_status()
            return resp.json() or []
        except (httpx.HTTPError, Exception) as exc:
            logger.warning("HN: failed to fetch %s: %s", endpoint, exc)
            return []

    async def _fetch_story(self, client: httpx.AsyncClient, story_id: int) -> Signal | None:
        try:
            resp = await client.get(f"{HN_API}/item/{story_id}.json")
            resp.raise_for_status()
            data = resp.json()
            if not data or data.get("type") != "story":
                return None

            score = data.get("score", 0)
            descendants = data.get("descendants", 0)
            created = data.get("time", 0)
            age_hours = max(
                (datetime.now(timezone.utc).timestamp() - created) / 3600, 0.1
            )

            return Signal(
                source=self.name,
                title=data.get("title", ""),
                url=data.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                content_preview=data.get("title", "")[:200],
                timestamp=datetime.fromtimestamp(created, tz=timezone.utc),
                engagement_score=float(score + descendants),
                velocity_score=round(float(score + descendants) / age_hours, 2),
            )
        except (httpx.HTTPError, Exception) as exc:
            logger.debug("HN: failed to fetch story %d: %s", story_id, exc)
            return None
