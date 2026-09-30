"""Trend analysis engine — the core of Zeitgeist."""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from zeitgeist.ai import (
    generate_fallback_predictions,
    predict_with_anthropic,
    predict_with_openai,
)
from zeitgeist.models import Signal, TrendPrediction, TrendReport
from zeitgeist.sources.base import SignalCollector

logger = logging.getLogger(__name__)


async def collect_signals(sources: list[SignalCollector]) -> list[Signal]:
    """Gather signals from all enabled sources concurrently."""
    tasks = [source.collect() for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    signals: list[Signal] = []
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            logger.error("Collector %s failed: %s", source.name, result)
        else:
            signals.extend(result)

    logger.info("Collected %d total signals from %d sources", len(signals), len(sources))
    return signals


def analyze_velocity(signals: list[Signal]) -> list[Signal]:
    """Re-compute velocity scores with cross-source boosting.

    Signals that appear across multiple sources get a velocity bonus.
    """
    title_lower_map: dict[str, list[Signal]] = defaultdict(list)
    for sig in signals:
        key = sig.title.lower().strip()
        title_lower_map[key].append(sig)

    boosted: list[Signal] = []
    for sig in signals:
        key = sig.title.lower().strip()
        cross_source_count = len({s.source for s in title_lower_map[key]})
        boost = 1.0 + (cross_source_count - 1) * 0.5
        boosted.append(
            sig.model_copy(
                update={"velocity_score": round(sig.velocity_score * boost, 2)}
            )
        )
    return boosted


def detect_emerging_patterns(signals: list[Signal]) -> list[list[Signal]]:
    """Cluster related signals into pattern groups.

    Uses keyword overlap and source diversity to form clusters.
    """
    if not signals:
        return []

    sorted_sigs = sorted(signals, key=lambda s: s.velocity_score, reverse=True)
    clusters: list[list[Signal]] = []
    assigned: set[int] = set()

    for i, anchor in enumerate(sorted_sigs):
        if i in assigned:
            continue

        cluster = [anchor]
        assigned.add(i)

        for j, candidate in enumerate(sorted_sigs):
            if j in assigned:
                continue
            if _is_related(anchor, candidate):
                cluster.append(candidate)
                assigned.add(j)

        clusters.append(cluster)

    clusters.sort(key=lambda c: sum(s.velocity_score for s in c), reverse=True)
    return clusters[:20]


def _is_related(a: Signal, b: Signal) -> bool:
    """Determine whether two signals are about the same topic."""
    stop = {"the", "a", "an", "is", "are", "was", "for", "in", "on", "to", "and", "of", "with", "new"}
    words_a = {w.lower() for w in a.title.split() if len(w) > 2 and w.lower() not in stop}
    words_b = {w.lower() for w in b.title.split() if len(w) > 2 and w.lower() not in stop}
    overlap = len(words_a & words_b)
    return overlap >= 2


async def generate_predictions(patterns: list[list[Signal]]) -> list[TrendPrediction]:
    """Generate predictions using AI or fallback heuristics."""
    all_signals = [sig for cluster in patterns for sig in cluster]

    if os.getenv("ANTHROPIC_API_KEY"):
        logger.info("Using Anthropic for predictions")
        predictions = await predict_with_anthropic(all_signals)
        if predictions:
            for pred, cluster in zip(predictions, patterns):
                pred.supporting_signals = cluster[:5]
            return predictions

    if os.getenv("OPENAI_API_KEY"):
        logger.info("Using OpenAI for predictions")
        predictions = await predict_with_openai(all_signals)
        if predictions:
            for pred, cluster in zip(predictions, patterns):
                pred.supporting_signals = cluster[:5]
            return predictions

    logger.info("No LLM API key — using heuristic predictions")
    return generate_fallback_predictions(all_signals)


def create_report(
    predictions: list[TrendPrediction], time_horizon_hours: int = 48
) -> TrendReport:
    """Build a TrendReport from a list of predictions."""
    predictions = sorted(predictions, key=lambda p: p.confidence, reverse=True)

    meta_trends: list[str] = []
    categories = defaultdict(int)
    for pred in predictions:
        categories[pred.category.value] += 1
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        if count >= 2:
            meta_trends.append(f"Multiple signals in {cat.replace('_', '/')} ({count} predictions)")

    for pred in predictions:
        if pred.predicted_peak_date is None:
            hours_offset = int(24 + (1 - pred.confidence) * 48)
            pred.predicted_peak_date = datetime.now(timezone.utc) + timedelta(hours=hours_offset)

    return TrendReport(
        predictions=predictions,
        meta_trends=meta_trends,
        time_horizon_hours=time_horizon_hours,
    )


async def run_full_scan(sources: list[SignalCollector]) -> TrendReport:
    """Execute the full scan → analyze → predict → report pipeline."""
    signals = await collect_signals(sources)
    signals = analyze_velocity(signals)
    patterns = detect_emerging_patterns(signals)
    predictions = await generate_predictions(patterns)
    return create_report(predictions)
