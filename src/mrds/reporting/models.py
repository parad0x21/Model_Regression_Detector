"""Report models — template-ready context plus the rendered artifact.

Context models are the clean boundary between report *logic* (the builder, which
selects/derives what to show) and report *presentation* (the Jinja2 templates,
which only read context fields). They reuse existing domain models, so they are
feature-agnostic by construction.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mrds.evaluation.models import (
    CaseResult,
    LatencyStats,
    ScorerStats,
    SegmentStats,
    TokenStats,
)
from mrds.regression.models import MetricComparison


class ReportFormat(StrEnum):
    """Output format for a rendered report."""

    HTML = "html"
    MARKDOWN = "markdown"


class RenderedReport(BaseModel):
    """A rendered report: its title, format, and content string."""

    model_config = ConfigDict(frozen=True)

    title: str
    format: ReportFormat
    content: str


class PromotionStatus(BaseModel):
    """A template-friendly view of a promotion eligibility decision."""

    model_config = ConfigDict(frozen=True)

    eligible: bool
    reasons: list[str] = Field(default_factory=list)
    severity: str | None = None


class EvaluationReportContext(BaseModel):
    """All data an evaluation report template needs."""

    model_config = ConfigDict(frozen=True)

    title: str
    generated_at: datetime

    feature: str
    run_id: str
    model: str
    prompt_version: str
    prompt_hash: str
    dataset_version: str
    dataset_hash: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float

    total_cases: int
    passed: int
    failed: int
    errored: int
    pass_rate: float

    scorers: list[ScorerStats] = Field(default_factory=list)
    segments: list[SegmentStats] = Field(default_factory=list)
    segment_field: str | None = None
    latency: LatencyStats
    tokens: TokenStats
    cases: list[CaseResult] = Field(default_factory=list)


class RegressionReportContext(BaseModel):
    """All data a regression report template needs."""

    model_config = ConfigDict(frozen=True)

    title: str
    generated_at: datetime

    feature: str
    baseline_run_id: str
    candidate_run_id: str
    baseline_prompt_version: str
    candidate_prompt_version: str
    baseline_dataset_version: str
    candidate_dataset_version: str
    prompt_changed: bool
    dataset_changed: bool

    severity: str
    is_blocking: bool
    warning_count: int
    critical_count: int

    regressed: list[MetricComparison] = Field(default_factory=list)
    improved: list[MetricComparison] = Field(default_factory=list)
    unchanged_count: int = 0

    promotion: PromotionStatus | None = None

    # Allow arbitrary extra context if a caller wants to extend a template.
    extra: dict[str, Any] = Field(default_factory=dict)
