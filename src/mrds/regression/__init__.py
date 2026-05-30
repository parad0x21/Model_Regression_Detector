"""Regression detection and the baseline-promotion workflow.

Compares two :class:`~mrds.evaluation.models.EvaluationResult` objects and produces
a :class:`RegressionResult`. Feature/dataset/prompt-agnostic; no persistence yet.
"""

from mrds.regression.detector import (
    RegressionDetector,
    classify_metric_kind,
    flatten_metrics,
)
from mrds.regression.errors import PromotionNotEligibleError, RegressionError
from mrds.regression.models import (
    Baseline,
    BaselineCandidate,
    MetricComparison,
    MetricKind,
    PromotionEligibility,
    RegressionResult,
    Severity,
    worst_severity,
)
from mrds.regression.promotion import BaselinePromoter
from mrds.regression.thresholds import (
    ErrorThresholds,
    IncreaseThresholds,
    QualityThresholds,
    ThresholdConfig,
)

__all__ = [
    "Baseline",
    "BaselineCandidate",
    "BaselinePromoter",
    "ErrorThresholds",
    "IncreaseThresholds",
    "MetricComparison",
    "MetricKind",
    "PromotionEligibility",
    "PromotionNotEligibleError",
    "QualityThresholds",
    "RegressionDetector",
    "RegressionError",
    "RegressionResult",
    "Severity",
    "ThresholdConfig",
    "classify_metric_kind",
    "flatten_metrics",
    "worst_severity",
]
