"""MCP server for Zeitgeist — expose trend scanning to AI assistants."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from zeitgeist.analyzer import run_full_scan
from zeitgeist.models import TrendReport
from zeitgeist.sources import GitHubCollector, HackerNewsCollector, MockCollector, RedditCollector
from zeitgeist.store import ZeitgeistStore

mcp = FastMCP(
    "Zeitgeist",
    description="AI trend prediction engine — predicts trending topics 24-72h before they trend.",
)


def _get_sources(use_mock: bool = False):
    if use_mock:
        return [MockCollector()]
    return [HackerNewsCollector(), RedditCollector(), GitHubCollector()]


@mcp.tool()
async def scan_trends(use_mock: bool = False, time_horizon_hours: int = 48) -> str:
    """Scan all signal sources and generate trend predictions.

    Args:
        use_mock: Use mock data instead of live APIs (for testing).
        time_horizon_hours: How far ahead to predict (default 48h).

    Returns:
        JSON report with trend predictions, confidence scores, and explanations.
    """
    sources = _get_sources(use_mock=use_mock)
    report = await run_full_scan(sources)
    report.time_horizon_hours = time_horizon_hours

    store = ZeitgeistStore()
    await store.initialize()
    await store.store_report(report)

    return report.model_dump_json(indent=2)


@mcp.tool()
async def get_predictions(limit: int = 10) -> str:
    """Get the most recent trend predictions from the database.

    Args:
        limit: Maximum number of predictions to return.

    Returns:
        JSON array of trend predictions with confidence scores.
    """
    store = ZeitgeistStore()
    await store.initialize()
    predictions = await store.get_recent_predictions(limit=limit)

    if not predictions:
        return json.dumps({"message": "No predictions yet. Run scan_trends first."})

    return json.dumps(
        [p.model_dump(mode="json", exclude={"supporting_signals"}) for p in predictions],
        indent=2,
    )


@mcp.tool()
async def explain_zeitgeist() -> str:
    """Explain what Zeitgeist is and how to use it.

    Returns:
        Description of Zeitgeist capabilities and usage instructions.
    """
    return json.dumps(
        {
            "name": "Zeitgeist",
            "tagline": "Google Trends tells you NOW. Zeitgeist tells you TOMORROW.",
            "description": (
                "Zeitgeist is an AI trend prediction engine that monitors early signals "
                "from multiple sources (HackerNews, Reddit, GitHub trending, ArXiv papers, "
                "patent filings, job postings) and uses AI to identify patterns and emerging "
                "trends 24-72 hours BEFORE they peak."
            ),
            "tools": {
                "scan_trends": "Scan all sources and generate fresh predictions",
                "get_predictions": "View the latest stored predictions",
                "explain_zeitgeist": "This explanation",
            },
            "sources": [
                "HackerNews (top + new stories)",
                "Reddit (rising posts from tech subreddits)",
                "GitHub (trending repositories)",
            ],
            "output": (
                "Each prediction includes: topic, category, confidence score (0-1), "
                "predicted peak date, velocity, explanation, and recommended actions."
            ),
        },
        indent=2,
    )


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
