"""FastAPI application for the Zeitgeist API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from zeitgeist.analyzer import run_full_scan
from zeitgeist.models import TrendPrediction, TrendReport
from zeitgeist.sources import GitHubCollector, HackerNewsCollector, MockCollector, RedditCollector
from zeitgeist.store import ZeitgeistStore

app = FastAPI(
    title="Zeitgeist API",
    description="AI that predicts trending topics before they trend.",
    version="0.1.0",
)


class ScanRequest(BaseModel):
    use_mock: bool = False
    time_horizon_hours: int = 48


class ScanResponse(BaseModel):
    status: str
    report: TrendReport


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


class SourceInfo(BaseModel):
    name: str
    type: str
    status: str
    description: str


def _get_sources(use_mock: bool = False):
    if use_mock:
        return [MockCollector()]
    return [HackerNewsCollector(), RedditCollector(), GitHubCollector()]


@app.get("/health", response_model=HealthResponse)
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
    }


@app.post("/api/v1/scan", response_model=ScanResponse)
async def scan_trends(request: ScanRequest | None = None) -> dict[str, Any]:
    """Trigger a full scan of all sources and generate predictions."""
    req = request or ScanRequest()
    sources = _get_sources(use_mock=req.use_mock)

    try:
        report = await run_full_scan(sources)
        report.time_horizon_hours = req.time_horizon_hours

        store = ZeitgeistStore()
        await store.initialize()
        await store.store_report(report)

        return {"status": "completed", "report": report}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/predictions", response_model=list[TrendPrediction])
async def get_predictions(limit: int = 20) -> list[TrendPrediction]:
    """Get the most recent trend predictions."""
    store = ZeitgeistStore()
    await store.initialize()
    return await store.get_recent_predictions(limit=limit)


@app.get("/api/v1/sources", response_model=list[SourceInfo])
async def list_sources() -> list[dict[str, str]]:
    """List all available signal sources."""
    return [
        {
            "name": "HackerNews",
            "type": "hackernews",
            "status": "active",
            "description": "Top & new stories via Firebase API",
        },
        {
            "name": "Reddit",
            "type": "reddit",
            "status": "active",
            "description": "Rising posts from tech subreddits",
        },
        {
            "name": "GitHub",
            "type": "github",
            "status": "active",
            "description": "Trending repositories via search API",
        },
        {
            "name": "Mock",
            "type": "mock",
            "status": "testing",
            "description": "Realistic sample data for testing",
        },
    ]
