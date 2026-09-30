"""GitHub signal collector — fetches trending repositories via the search API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from zeitgeist.models import Signal
from zeitgeist.sources.base import SignalCollector

logger = logging.getLogger(__name__)


class GitHubCollector(SignalCollector):
    """Collect signals from GitHub trending repositories (via search API)."""

    name = "github"

    async def collect(self) -> list[Signal]:
        signals: list[Signal] = []
        since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"created:>{since}",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 30,
                    },
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "Zeitgeist/0.1",
                    },
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])

                for repo in items:
                    stars = repo.get("stargazers_count", 0)
                    forks = repo.get("forks_count", 0)
                    created = repo.get("created_at", "")
                    try:
                        ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        ts = datetime.now(timezone.utc)

                    age_hours = max(
                        (datetime.now(timezone.utc) - ts).total_seconds() / 3600,
                        0.1,
                    )

                    signals.append(
                        Signal(
                            source=self.name,
                            title=repo.get("full_name", ""),
                            url=repo.get("html_url", ""),
                            content_preview=(repo.get("description") or "")[:200],
                            timestamp=ts,
                            engagement_score=float(stars + forks),
                            velocity_score=round(float(stars + forks) / age_hours, 2),
                        )
                    )
            except (httpx.HTTPError, Exception) as exc:
                logger.warning("GitHub: failed to fetch trending: %s", exc)

        logger.info("GitHub collected %d signals", len(signals))
        return signals
