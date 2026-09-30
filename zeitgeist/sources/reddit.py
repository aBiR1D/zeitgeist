"""Reddit signal collector — fetches rising posts from key subreddits via JSON API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from zeitgeist.models import Signal
from zeitgeist.sources.base import SignalCollector

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = [
    "technology",
    "programming",
    "machinelearning",
    "artificial",
    "startups",
    "netsec",
    "devops",
    "science",
]

HEADERS = {
    "User-Agent": "Zeitgeist/0.1 (trend-predictor; educational)",
}


class RedditCollector(SignalCollector):
    """Collect signals from Reddit rising and hot posts."""

    name = "reddit"

    def __init__(self, subreddits: list[str] | None = None) -> None:
        self.subreddits = subreddits or DEFAULT_SUBREDDITS

    async def collect(self) -> list[Signal]:
        signals: list[Signal] = []
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
            for sub in self.subreddits:
                signals.extend(await self._fetch_subreddit(client, sub))

        logger.info("Reddit collected %d signals", len(signals))
        return signals

    async def _fetch_subreddit(
        self, client: httpx.AsyncClient, subreddit: str
    ) -> list[Signal]:
        results: list[Signal] = []
        for listing in ("rising", "hot"):
            try:
                resp = await client.get(
                    f"https://www.reddit.com/r/{subreddit}/{listing}.json",
                    params={"limit": 10, "raw_json": 1},
                )
                resp.raise_for_status()
                data = resp.json()
                children = data.get("data", {}).get("children", [])

                for child in children:
                    post = child.get("data", {})
                    if not post.get("title"):
                        continue

                    score = post.get("score", 0)
                    num_comments = post.get("num_comments", 0)
                    created = post.get("created_utc", 0)
                    age_hours = max(
                        (datetime.now(timezone.utc).timestamp() - created) / 3600,
                        0.1,
                    )

                    results.append(
                        Signal(
                            source=self.name,
                            title=post["title"],
                            url=f"https://reddit.com{post.get('permalink', '')}",
                            content_preview=(post.get("selftext") or post["title"])[:200],
                            timestamp=datetime.fromtimestamp(created, tz=timezone.utc),
                            engagement_score=float(score + num_comments),
                            velocity_score=round(float(score + num_comments) / age_hours, 2),
                        )
                    )
            except (httpx.HTTPError, Exception) as exc:
                logger.warning("Reddit: failed to fetch r/%s/%s: %s", subreddit, listing, exc)

        return results
