"""Mock signal collector for testing with realistic sample data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from zeitgeist.models import Signal
from zeitgeist.sources.base import SignalCollector

MOCK_SIGNALS = [
    Signal(
        source="mock",
        title="New Rust-based JavaScript runtime outperforms Node.js by 3x",
        url="https://example.com/rust-js-runtime",
        content_preview="A new Rust-based JavaScript runtime shows 3x performance gains...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        engagement_score=342.0,
        velocity_score=171.0,
    ),
    Signal(
        source="mock",
        title="Apple announces on-device LLM for iOS 20",
        url="https://example.com/apple-llm",
        content_preview="Apple reveals plans for a fully on-device large language model...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=4),
        engagement_score=1280.0,
        velocity_score=320.0,
    ),
    Signal(
        source="mock",
        title="EU passes landmark AI liability directive",
        url="https://example.com/eu-ai-liability",
        content_preview="The European Union has passed a comprehensive AI liability...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=6),
        engagement_score=567.0,
        velocity_score=94.5,
    ),
    Signal(
        source="mock",
        title="Novel protein folding technique achieves 99.8% accuracy",
        url="https://example.com/protein-folding",
        content_preview="Researchers demonstrate a new protein folding approach...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
        engagement_score=210.0,
        velocity_score=210.0,
    ),
    Signal(
        source="mock",
        title="GitHub Copilot now generates full test suites automatically",
        url="https://example.com/copilot-tests",
        content_preview="GitHub unveils Copilot's new ability to generate complete...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
        engagement_score=890.0,
        velocity_score=296.7,
    ),
    Signal(
        source="mock",
        title="Zero-knowledge proofs enable private smart contracts on Ethereum",
        url="https://example.com/zk-ethereum",
        content_preview="A new protocol brings full privacy to Ethereum smart contracts...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=5),
        engagement_score=445.0,
        velocity_score=89.0,
    ),
    Signal(
        source="mock",
        title="Quantum error correction breakthrough at Google",
        url="https://example.com/quantum-google",
        content_preview="Google achieves a major milestone in quantum error correction...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        engagement_score=1100.0,
        velocity_score=550.0,
    ),
    Signal(
        source="mock",
        title="WebAssembly 3.0 spec finalized with GC and threads",
        url="https://example.com/wasm-3",
        content_preview="The WebAssembly 3.0 specification has been finalized...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=8),
        engagement_score=320.0,
        velocity_score=40.0,
    ),
    Signal(
        source="mock",
        title="Startup raises $100M for autonomous coding agents",
        url="https://example.com/coding-agents",
        content_preview="An AI startup has raised $100M Series B for autonomous...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
        engagement_score=670.0,
        velocity_score=670.0,
    ),
    Signal(
        source="mock",
        title="Critical supply chain vulnerability found in popular npm packages",
        url="https://example.com/npm-vuln",
        content_preview="Security researchers discover a supply chain attack affecting...",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
        engagement_score=980.0,
        velocity_score=326.7,
    ),
]


class MockCollector(SignalCollector):
    """Returns realistic sample data for testing and demos."""

    name = "mock"

    async def collect(self) -> list[Signal]:
        return list(MOCK_SIGNALS)
