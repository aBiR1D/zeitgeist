"""LLM abstraction layer for Zeitgeist trend analysis."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from zeitgeist.models import Signal, TrendCategory, TrendPrediction

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are Zeitgeist, an AI trend prediction engine. Given a set of signals \
collected from various sources (HackerNews, Reddit, GitHub, ArXiv, etc.), \
identify emerging trends that are likely to peak in the next 24-72 hours.

For each trend you identify, provide:
1. A concise topic name
2. A category (one of: ai_ml, programming, security, devops, startup, science, crypto_web3, regulation, hardware, culture, other)
3. A confidence score (0.0 to 1.0)
4. An explanation of WHY this will trend
5. Recommended actions for someone who wants to stay ahead

Respond ONLY with valid JSON — an array of objects with keys:
topic, category, confidence, explanation, recommended_actions (array of strings)
"""


def _build_signals_prompt(signals: list[Signal]) -> str:
    """Format signals into a prompt for the LLM."""
    lines = ["Here are the current signals:\n"]
    for i, sig in enumerate(signals, 1):
        lines.append(
            f"{i}. [{sig.source}] {sig.title}\n"
            f"   Engagement: {sig.engagement_score:.0f} | Velocity: {sig.velocity_score:.1f}\n"
            f"   Preview: {sig.content_preview[:120]}\n"
        )
    lines.append(
        "\nIdentify the top emerging trends from these signals. "
        "Return JSON array of predictions."
    )
    return "\n".join(lines)


async def predict_with_anthropic(signals: list[Signal]) -> list[TrendPrediction]:
    """Generate predictions using the Anthropic Claude API."""
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping AI prediction")
        return []

    client = anthropic.AsyncAnthropic(api_key=api_key)
    user_prompt = _build_signals_prompt(signals)

    try:
        message = await client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text
        return _parse_predictions(raw, signals)
    except Exception as exc:
        logger.error("Anthropic API call failed: %s", exc)
        return []


async def predict_with_openai(signals: list[Signal]) -> list[TrendPrediction]:
    """Generate predictions using the OpenAI API."""
    try:
        import openai
    except ImportError:
        logger.error("openai package not installed")
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — skipping AI prediction")
        return []

    client = openai.AsyncOpenAI(api_key=api_key)
    user_prompt = _build_signals_prompt(signals)

    try:
        resp = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            temperature=0.7,
        )
        raw = resp.choices[0].message.content or "[]"
        return _parse_predictions(raw, signals)
    except Exception as exc:
        logger.error("OpenAI API call failed: %s", exc)
        return []


def _parse_predictions(raw_json: str, signals: list[Signal]) -> list[TrendPrediction]:
    """Parse LLM JSON output into TrendPrediction objects."""
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        items: list[dict[str, Any]] = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON: %s", raw_json[:200])
        return []

    predictions: list[TrendPrediction] = []
    for item in items:
        try:
            category = item.get("category", "other")
            try:
                cat = TrendCategory(category)
            except ValueError:
                cat = TrendCategory.OTHER

            predictions.append(
                TrendPrediction(
                    topic=item["topic"],
                    category=cat,
                    confidence=max(0.0, min(1.0, float(item.get("confidence", 0.5)))),
                    explanation=item.get("explanation", ""),
                    recommended_actions=item.get("recommended_actions", []),
                    current_signals_count=len(signals),
                    velocity=sum(s.velocity_score for s in signals) / max(len(signals), 1),
                )
            )
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed prediction: %s", exc)

    return predictions


def generate_fallback_predictions(signals: list[Signal]) -> list[TrendPrediction]:
    """Heuristic-based predictions when no LLM API key is available.

    Groups signals by keyword overlap and scores by aggregate velocity.
    """
    if not signals:
        return []

    sorted_signals = sorted(signals, key=lambda s: s.velocity_score, reverse=True)
    predictions: list[TrendPrediction] = []
    seen_topics: set[str] = set()

    for sig in sorted_signals[:10]:
        topic = sig.title[:80]
        if topic in seen_topics:
            continue
        seen_topics.add(topic)

        related = [
            s
            for s in signals
            if s is not sig
            and _keyword_overlap(sig.title.lower(), s.title.lower()) >= 2
        ]

        avg_velocity = (
            sig.velocity_score + sum(r.velocity_score for r in related)
        ) / (1 + len(related))
        confidence = min(1.0, avg_velocity / 500.0 + len(related) * 0.1)

        predictions.append(
            TrendPrediction(
                topic=topic,
                category=TrendCategory.OTHER,
                confidence=round(confidence, 2),
                current_signals_count=1 + len(related),
                velocity=round(avg_velocity, 2),
                supporting_signals=[sig] + related,
                explanation=(
                    f"High velocity signal ({sig.velocity_score:.1f}) "
                    f"with {len(related)} related signals across sources."
                ),
                recommended_actions=["Monitor this topic closely", "Prepare content around it"],
            )
        )

    predictions.sort(key=lambda p: p.confidence, reverse=True)
    return predictions[:10]


def _keyword_overlap(a: str, b: str) -> int:
    """Count overlapping significant words between two strings."""
    stop_words = {"the", "a", "an", "is", "are", "was", "for", "in", "on", "to", "and", "of", "with", "new"}
    words_a = {w for w in a.split() if len(w) > 2 and w not in stop_words}
    words_b = {w for w in b.split() if len(w) > 2 and w not in stop_words}
    return len(words_a & words_b)
