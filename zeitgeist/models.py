"""Pydantic models for Zeitgeist."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceName(str, Enum):
    """Supported signal source names."""

    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    GITHUB = "github"
    ARXIV = "arxiv"
    PATENTS = "patents"
    JOBS = "jobs"
    MOCK = "mock"


class TrendCategory(str, Enum):
    """Categories for trend predictions."""

    AI_ML = "ai_ml"
    PROGRAMMING = "programming"
    SECURITY = "security"
    DEVOPS = "devops"
    STARTUP = "startup"
    SCIENCE = "science"
    CRYPTO_WEB3 = "crypto_web3"
    REGULATION = "regulation"
    HARDWARE = "hardware"
    CULTURE = "culture"
    OTHER = "other"


class Signal(BaseModel):
    """A single signal from a source indicating potential trend activity."""

    source: str = Field(description="Source that produced this signal")
    title: str = Field(description="Title or headline of the signal")
    url: Optional[str] = Field(default=None, description="URL to the original content")
    content_preview: str = Field(
        default="", description="Short preview of the content"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this signal was captured",
    )
    engagement_score: float = Field(
        default=0.0, ge=0.0, description="Normalized engagement score (upvotes, stars, etc.)"
    )
    velocity_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Rate of engagement growth — higher means faster acceleration",
    )


class SignalSource(BaseModel):
    """Configuration for a signal source."""

    name: str = Field(description="Source identifier")
    enabled: bool = Field(default=True, description="Whether this source is active")
    weight: float = Field(
        default=1.0, ge=0.0, le=5.0, description="Weight multiplier for signals from this source"
    )


class TrendPrediction(BaseModel):
    """A prediction about an emerging trend."""

    topic: str = Field(description="The predicted trending topic")
    category: TrendCategory = Field(default=TrendCategory.OTHER, description="Trend category")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score from 0 (uncertain) to 1 (very confident)"
    )
    predicted_peak_date: Optional[datetime] = Field(
        default=None, description="When this topic is expected to peak"
    )
    current_signals_count: int = Field(
        default=0, ge=0, description="Number of signals supporting this prediction"
    )
    velocity: float = Field(default=0.0, description="Composite velocity score across signals")
    supporting_signals: list[Signal] = Field(
        default_factory=list, description="Signals that support this prediction"
    )
    explanation: str = Field(default="", description="AI-generated explanation of the prediction")
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Suggested actions to take advantage of this trend",
    )


class TrendReport(BaseModel):
    """A complete trend report with predictions and metadata."""

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this report was generated",
    )
    predictions: list[TrendPrediction] = Field(
        default_factory=list, description="Ordered list of predictions"
    )
    top_prediction: Optional[TrendPrediction] = Field(
        default=None, description="Highest-confidence prediction"
    )
    meta_trends: list[str] = Field(
        default_factory=list,
        description="Higher-level meta-trends observed across predictions",
    )
    time_horizon_hours: int = Field(
        default=48, description="How far ahead these predictions look"
    )

    def model_post_init(self, __context: object) -> None:
        if self.predictions and self.top_prediction is None:
            self.top_prediction = max(self.predictions, key=lambda p: p.confidence)


class HistoricalTrend(BaseModel):
    """A historical trend for accuracy tracking."""

    topic: str = Field(description="The predicted topic")
    predicted_at: datetime = Field(description="When the prediction was made")
    actual_peak: Optional[datetime] = Field(
        default=None, description="When the topic actually peaked (if it did)"
    )
    accuracy_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="How accurate the prediction was (0-1)",
    )
