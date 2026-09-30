"""SQLite storage for signals, predictions, and accuracy tracking."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from zeitgeist.models import HistoricalTrend, Signal, TrendPrediction, TrendReport

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.getenv(
    "ZEITGEIST_DB", str(Path.home() / ".zeitgeist" / "zeitgeist.db")
)

SCHEMA = """\
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    content_preview TEXT,
    timestamp TEXT NOT NULL,
    engagement_score REAL DEFAULT 0,
    velocity_score REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    category TEXT,
    confidence REAL NOT NULL,
    predicted_peak_date TEXT,
    current_signals_count INTEGER DEFAULT 0,
    velocity REAL DEFAULT 0,
    explanation TEXT,
    recommended_actions TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TEXT NOT NULL,
    time_horizon_hours INTEGER DEFAULT 48,
    meta_trends TEXT,
    prediction_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accuracy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    topic TEXT NOT NULL,
    predicted_at TEXT NOT NULL,
    actual_peak TEXT,
    accuracy_score REAL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);
"""


class ZeitgeistStore:
    """Async SQLite store for Zeitgeist data."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH

    async def _ensure_dir(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        await self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def store_signals(self, signals: list[Signal]) -> None:
        """Persist a batch of signals."""
        await self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT INTO signals (source, title, url, content_preview,
                   timestamp, engagement_score, velocity_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        s.source,
                        s.title,
                        s.url,
                        s.content_preview,
                        s.timestamp.isoformat(),
                        s.engagement_score,
                        s.velocity_score,
                    )
                    for s in signals
                ],
            )
            await db.commit()

    async def store_predictions(self, predictions: list[TrendPrediction]) -> list[int]:
        """Persist predictions and return their IDs."""
        await self._ensure_dir()
        ids: list[int] = []
        async with aiosqlite.connect(self.db_path) as db:
            for pred in predictions:
                cursor = await db.execute(
                    """INSERT INTO predictions (topic, category, confidence,
                       predicted_peak_date, current_signals_count, velocity,
                       explanation, recommended_actions)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        pred.topic,
                        pred.category.value,
                        pred.confidence,
                        pred.predicted_peak_date.isoformat() if pred.predicted_peak_date else None,
                        pred.current_signals_count,
                        pred.velocity,
                        pred.explanation,
                        json.dumps(pred.recommended_actions),
                    ),
                )
                ids.append(cursor.lastrowid or 0)
            await db.commit()
        return ids

    async def store_report(self, report: TrendReport) -> int:
        """Persist a report summary and its predictions."""
        await self._ensure_dir()
        pred_ids = await self.store_predictions(report.predictions)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO reports (generated_at, time_horizon_hours,
                   meta_trends, prediction_count)
                   VALUES (?, ?, ?, ?)""",
                (
                    report.generated_at.isoformat(),
                    report.time_horizon_hours,
                    json.dumps(report.meta_trends),
                    len(report.predictions),
                ),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def get_recent_predictions(self, limit: int = 20) -> list[TrendPrediction]:
        """Fetch the most recent predictions."""
        await self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()

        predictions: list[TrendPrediction] = []
        for row in rows:
            try:
                actions = json.loads(row["recommended_actions"] or "[]")
            except (json.JSONDecodeError, TypeError):
                actions = []

            peak = None
            if row["predicted_peak_date"]:
                try:
                    peak = datetime.fromisoformat(row["predicted_peak_date"])
                except ValueError:
                    pass

            predictions.append(
                TrendPrediction(
                    topic=row["topic"],
                    category=row["category"] or "other",
                    confidence=row["confidence"],
                    predicted_peak_date=peak,
                    current_signals_count=row["current_signals_count"] or 0,
                    velocity=row["velocity"] or 0.0,
                    explanation=row["explanation"] or "",
                    recommended_actions=actions,
                )
            )
        return predictions

    async def get_prediction_accuracy(self) -> list[HistoricalTrend]:
        """Return historical accuracy data."""
        await self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM accuracy ORDER BY predicted_at DESC LIMIT 50"
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            HistoricalTrend(
                topic=row["topic"],
                predicted_at=datetime.fromisoformat(row["predicted_at"]),
                actual_peak=(
                    datetime.fromisoformat(row["actual_peak"])
                    if row["actual_peak"]
                    else None
                ),
                accuracy_score=row["accuracy_score"],
            )
            for row in rows
        ]

    async def record_accuracy(
        self,
        prediction_id: int,
        topic: str,
        predicted_at: datetime,
        actual_peak: Optional[datetime] = None,
        accuracy_score: Optional[float] = None,
    ) -> None:
        """Record accuracy for a past prediction."""
        await self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO accuracy (prediction_id, topic, predicted_at,
                   actual_peak, accuracy_score)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    prediction_id,
                    topic,
                    predicted_at.isoformat(),
                    actual_peak.isoformat() if actual_peak else None,
                    accuracy_score,
                ),
            )
            await db.commit()
