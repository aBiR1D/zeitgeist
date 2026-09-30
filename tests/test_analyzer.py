"""Tests for the Zeitgeist analysis engine."""

import pytest

from zeitgeist.analyzer import (
    analyze_velocity,
    collect_signals,
    create_report,
    detect_emerging_patterns,
)
from zeitgeist.ai import generate_fallback_predictions
from zeitgeist.models import Signal, TrendReport
from zeitgeist.sources.mock import MockCollector


@pytest.mark.asyncio
async def test_collect_signals():
    sources = [MockCollector()]
    signals = await collect_signals(sources)
    assert len(signals) > 0
    assert all(isinstance(s, Signal) for s in signals)


@pytest.mark.asyncio
async def test_collect_signals_multiple_sources():
    sources = [MockCollector(), MockCollector()]
    signals = await collect_signals(sources)
    assert len(signals) > 5


def test_analyze_velocity():
    signals = [
        Signal(source="a", title="Rust runtime performance", engagement_score=100, velocity_score=50),
        Signal(source="b", title="Rust runtime performance", engagement_score=200, velocity_score=80),
        Signal(source="c", title="Something else entirely", engagement_score=50, velocity_score=25),
    ]
    boosted = analyze_velocity(signals)
    assert len(boosted) == 3

    rust_signals = [s for s in boosted if "Rust" in s.title]
    other_signals = [s for s in boosted if "Rust" not in s.title]
    assert rust_signals[0].velocity_score > 50
    assert other_signals[0].velocity_score == 25


def test_detect_emerging_patterns():
    signals = [
        Signal(source="hn", title="New JavaScript runtime built with Rust", velocity_score=100),
        Signal(source="reddit", title="Rust-based JavaScript runtime benchmarks", velocity_score=80),
        Signal(source="github", title="quantum computing breakthrough paper", velocity_score=60),
        Signal(source="hn", title="quantum computing reaches new milestone", velocity_score=50),
        Signal(source="reddit", title="Unrelated topic about cooking", velocity_score=10),
    ]
    patterns = detect_emerging_patterns(signals)
    assert len(patterns) >= 2
    assert all(isinstance(cluster, list) for cluster in patterns)
    assert all(isinstance(sig, Signal) for cluster in patterns for sig in cluster)


def test_detect_emerging_patterns_empty():
    patterns = detect_emerging_patterns([])
    assert patterns == []


def test_generate_fallback_predictions():
    signals = [
        Signal(source="hn", title="AI coding assistant revolution", velocity_score=500, engagement_score=1000),
        Signal(source="reddit", title="New AI coding tools compared", velocity_score=300, engagement_score=800),
        Signal(source="github", title="quantum computing framework release", velocity_score=200, engagement_score=400),
    ]
    predictions = generate_fallback_predictions(signals)
    assert len(predictions) > 0
    assert all(0 <= p.confidence <= 1 for p in predictions)
    assert predictions[0].confidence >= predictions[-1].confidence


def test_generate_fallback_predictions_empty():
    predictions = generate_fallback_predictions([])
    assert predictions == []


def test_create_report():
    from zeitgeist.models import TrendPrediction

    preds = [
        TrendPrediction(topic="AI tools", confidence=0.9, velocity=100),
        TrendPrediction(topic="Quantum", confidence=0.6, velocity=50),
    ]
    report = create_report(preds)
    assert isinstance(report, TrendReport)
    assert report.top_prediction is not None
    assert report.top_prediction.topic == "AI tools"
    assert len(report.predictions) == 2
    assert report.predictions[0].predicted_peak_date is not None


def test_create_report_sets_peak_dates():
    from zeitgeist.models import TrendPrediction

    preds = [TrendPrediction(topic="Test", confidence=0.5)]
    report = create_report(preds)
    assert report.predictions[0].predicted_peak_date is not None
