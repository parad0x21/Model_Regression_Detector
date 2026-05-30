"""Rich, structured result and metric models for an evaluation run.

All models are provider- and feature-agnostic: inputs/outputs are stored as plain
JSON-able dicts, and per-scorer / per-segment metrics are keyed by name so the
same models describe any feature's run.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mrds.core.interfaces import ScoreResult
from mrds.datasets.models import Difficulty


class CaseResult(BaseModel):
    """The outcome of evaluating a single dataset case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    expected_difficulty: Difficulty
    input: dict[str, Any]
    expected_output: dict[str, Any]
    actual_output: dict[str, Any] | None
    scores: list[ScoreResult] = Field(default_factory=list)
    passed: bool
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    error: str | None = None


class ScorerStats(BaseModel):
    """Aggregated statistics for one scorer across all evaluated cases."""

    model_config = ConfigDict(frozen=True)

    name: str
    mean_score: float
    pass_rate: float
    passed: int
    count: int


class SegmentStats(BaseModel):
    """Aggregated statistics for one segment (e.g. one category)."""

    model_config = ConfigDict(frozen=True)

    segment: str
    count: int
    passed: int
    pass_rate: float
    scorer_means: dict[str, float] = Field(default_factory=dict)


class LatencyStats(BaseModel):
    """Latency distribution across cases (milliseconds)."""

    model_config = ConfigDict(frozen=True)

    count: int
    total_ms: float
    mean_ms: float
    min_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float


class TokenStats(BaseModel):
    """Token usage across cases."""

    model_config = ConfigDict(frozen=True)

    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    mean_tokens_per_case: float


class AggregateMetrics(BaseModel):
    """All aggregate metrics for a run.

    Named metrics map onto scorers/segments generically:

    - *category accuracy* -> ``scorers['category_match'].mean_score``
    - *summary quality score* -> ``scorers['summary_quality'].mean_score``
    - *per-category accuracy* -> ``segments[<category>].scorer_means['category_match']``
    """

    model_config = ConfigDict(frozen=True)

    total_cases: int
    passed: int
    failed: int
    errored: int
    pass_rate: float
    scorers: dict[str, ScorerStats] = Field(default_factory=dict)
    segments: dict[str, SegmentStats] = Field(default_factory=dict)
    segment_field: str | None = None
    latency: LatencyStats
    tokens: TokenStats


class EvaluationResult(BaseModel):
    """The complete, structured result of an evaluation run."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    feature: str
    prompt_version: str
    prompt_hash: str
    dataset_version: str
    dataset_hash: str
    model: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    aggregate_metrics: AggregateMetrics
    per_case_results: list[CaseResult] = Field(default_factory=list)
