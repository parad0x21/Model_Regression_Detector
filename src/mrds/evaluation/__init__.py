"""Evaluation engine: execute a feature against a versioned dataset and prompt.

Feature-, prompt-, and dataset-agnostic. Produces rich structured results; no
persistence (that is a later sprint).
"""

from mrds.evaluation.config import EvaluationConfig
from mrds.evaluation.engine import EvaluationEngine
from mrds.evaluation.errors import EvaluationError
from mrds.evaluation.metrics import aggregate
from mrds.evaluation.models import (
    AggregateMetrics,
    CaseResult,
    EvaluationResult,
    LatencyStats,
    ScorerStats,
    SegmentStats,
    TokenStats,
)
from mrds.evaluation.scoring import score_case

__all__ = [
    "AggregateMetrics",
    "CaseResult",
    "EvaluationConfig",
    "EvaluationEngine",
    "EvaluationError",
    "EvaluationResult",
    "LatencyStats",
    "ScorerStats",
    "SegmentStats",
    "TokenStats",
    "aggregate",
    "score_case",
]
