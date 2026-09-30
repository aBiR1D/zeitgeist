"""Tests for signal source collectors (using mock collector)."""

import pytest

from zeitgeist.models import Signal
from zeitgeist.sources.mock import MockCollector


@pytest.mark.asyncio
async def test_mock_collector_returns_signals():
    collector = MockCollector()
    signals = await collector.collect()
    assert len(signals) > 0
    assert all(isinstance(s, Signal) for s in signals)


@pytest.mark.asyncio
async def test_mock_collector_name():
    collector = MockCollector()
    assert collector.name == "mock"


@pytest.mark.asyncio
async def test_mock_signals_have_required_fields():
    collector = MockCollector()
    signals = await collector.collect()

    for sig in signals:
        assert sig.source == "mock"
        assert sig.title
        assert sig.url
        assert sig.engagement_score > 0
        assert sig.velocity_score > 0


@pytest.mark.asyncio
async def test_mock_signals_have_realistic_data():
    collector = MockCollector()
    signals = await collector.collect()

    titles = [s.title for s in signals]
    assert any("Rust" in t for t in titles)
    assert any("AI" in t or "LLM" in t for t in titles)


@pytest.mark.asyncio
async def test_mock_collector_returns_consistent_count():
    collector = MockCollector()
    first = await collector.collect()
    second = await collector.collect()
    assert len(first) == len(second)


@pytest.mark.asyncio
async def test_mock_signals_velocity_scores():
    collector = MockCollector()
    signals = await collector.collect()

    velocities = [s.velocity_score for s in signals]
    assert max(velocities) > 100
    assert min(velocities) > 0
