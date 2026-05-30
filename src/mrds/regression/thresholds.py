"""Configurable regression thresholds.

Thresholds are organised by metric *kind* (quality / latency / tokens / errors),
with optional per-metric overrides for quality metrics. They are feature-agnostic:
nothing here references any specific metric like category accuracy.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QualityThresholds(BaseModel):
    """Thresholds for higher-is-better metrics (pass rate, scorer/segment means)."""

    model_config = ConfigDict(extra="forbid")

    warning_abs_drop: float = Field(default=0.02, ge=0.0)
    critical_abs_drop: float = Field(default=0.05, ge=0.0)
    warning_rel_drop: float = Field(default=0.05, ge=0.0)
    critical_rel_drop: float = Field(default=0.10, ge=0.0)


class IncreaseThresholds(BaseModel):
    """Relative-increase thresholds for lower-is-better metrics (latency, tokens)."""

    model_config = ConfigDict(extra="forbid")

    warning_rel_increase: float = Field(default=0.25, ge=0.0)
    critical_rel_increase: float = Field(default=0.50, ge=0.0)


class ErrorThresholds(BaseModel):
    """Absolute-count increase thresholds for errored cases."""

    model_config = ConfigDict(extra="forbid")

    warning_increase: int = Field(default=1, ge=0)
    critical_increase: int = Field(default=3, ge=0)


class ThresholdConfig(BaseModel):
    """The full set of thresholds used by the regression detector."""

    model_config = ConfigDict(extra="forbid")

    quality: QualityThresholds = Field(default_factory=QualityThresholds)
    latency: IncreaseThresholds = Field(default_factory=IncreaseThresholds)
    tokens: IncreaseThresholds = Field(default_factory=IncreaseThresholds)
    errors: ErrorThresholds = Field(default_factory=ErrorThresholds)
    #: Per-metric overrides for quality metrics, keyed by flattened metric name
    #: (e.g. "scorer.category_match.mean_score").
    per_metric: dict[str, QualityThresholds] = Field(default_factory=dict)
