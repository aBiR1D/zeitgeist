"""Tests for Zeitgeist Pydantic models."""

from datetime import datetime, timedelta, timezone

import pytest

from zeitgeist.models import (
    HistoricalTrend,
    Signal,
    SignalSource,
    TrendCategory,
    TrendPrediction,
    TrendReport,
)


class TestSignal:
    def test_create_minimal(self):
        sig = Signal(source="test", title="Test signal")
        assert sig.source == "test"
        assert sig.title == "Test signal"
        assert sig.url is None
        assert sig.engagement_score == 0.0
        assert sig.velocity_score == 0.0

    def test_create_full(self):
        now = datetime.now(timezone.utc)
        sig = Signal(
            source="hackernews",
            title="Big news",
            url="https://example.com",
            content_preview="Some preview text",
            timestamp=now,
            engagement_score=100.0,
            velocity_score=50.0,
        )
        assert sig.source == "hackernews"
        assert sig.url == "https://example.com"
        assert sig.engagement_score == 100.0
        assert sig.velocity_score == 50.0
        assert sig.timestamp == now

    def test_engagement_score_non_negative(self):
        with pytest.raises(Exception):
            Signal(source="test", title="bad", engagement_score=-1.0)

    def test_velocity_score_non_negative(self):
        with pytest.raises(Exception):
            Signal(source="test", title="bad", velocity_score=-1.0)


class TestSignalSource:
    def test_defaults(self):
        src = SignalSource(name="hackernews")
        assert src.enabled is True
        assert src.weight == 1.0

    def test_custom_weight(self):
        src = SignalSource(name="reddit", weight=2.5)
        assert src.weight == 2.5

    def test_weight_bounds(self):
        with pytest.raises(Exception):
            SignalSource(name="bad", weight=10.0)


class TestTrendPrediction:
    def test_create(self):
        pred = TrendPrediction(
            topic="Rust runtime",
            category=TrendCategory.PROGRAMMING,
            confidence=0.85,
            explanation="Multiple signals about Rust",
        )
        assert pred.topic == "Rust runtime"
        assert pred.confidence == 0.85
        assert pred.category == TrendCategory.PROGRAMMING

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            TrendPrediction(topic="bad", confidence=1.5)
        with pytest.raises(Exception):
            TrendPrediction(topic="bad", confidence=-0.1)

    def test_default_fields(self):
        pred = TrendPrediction(topic="test", confidence=0.5)
        assert pred.current_signals_count == 0
        assert pred.supporting_signals == []
        assert pred.recommended_actions == []


class TestTrendReport:
    def test_empty_report(self):
        report = TrendReport()
        assert report.predictions == []
        assert report.top_prediction is None
        assert report.time_horizon_hours == 48

    def test_auto_top_prediction(self):
        preds = [
            TrendPrediction(topic="Low", confidence=0.3),
            TrendPrediction(topic="High", confidence=0.9),
            TrendPrediction(topic="Mid", confidence=0.6),
        ]
        report = TrendReport(predictions=preds)
        assert report.top_prediction is not None
        assert report.top_prediction.topic == "High"
        assert report.top_prediction.confidence == 0.9

    def test_meta_trends(self):
        report = TrendReport(meta_trends=["AI is big", "Security concerns"])
        assert len(report.meta_trends) == 2


class TestHistoricalTrend:
    def test_create(self):
        now = datetime.now(timezone.utc)
        ht = HistoricalTrend(
            topic="Test trend",
            predicted_at=now,
            accuracy_score=0.75,
        )
        assert ht.topic == "Test trend"
        assert ht.actual_peak is None
        assert ht.accuracy_score == 0.75

    def test_with_actual_peak(self):
        now = datetime.now(timezone.utc)
        later = now + timedelta(hours=36)
        ht = HistoricalTrend(
            topic="Peaked",
            predicted_at=now,
            actual_peak=later,
            accuracy_score=0.9,
        )
        assert ht.actual_peak == later
