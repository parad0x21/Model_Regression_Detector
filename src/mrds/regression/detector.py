"""The regression comparison engine.

Takes two :class:`EvaluationResult` objects (baseline, candidate) and produces a
:class:`RegressionResult`. It is feature/dataset/prompt-agnostic: metric names are
**discovered dynamically** by flattening :class:`AggregateMetrics`, so nothing here
references category accuracy or any email-specific metric.
"""

from __future__ import annotations

from mrds.evaluation.models import AggregateMetrics, EvaluationResult
from mrds.observability.logging import get_logger
from mrds.regression.errors import RegressionError
from mrds.regression.models import (
    MetricComparison,
    MetricKind,
    RegressionResult,
    Severity,
    worst_severity,
)
from mrds.regression.thresholds import ThresholdConfig

logger = get_logger(__name__)


def flatten_metrics(metrics: AggregateMetrics) -> dict[str, float]:
    """Flatten aggregate metrics into a ``name -> value`` map.

    Scorer and segment names are discovered dynamically, so any feature's metrics
    are represented without hardcoding.
    """
    flat: dict[str, float] = {
        "pass_rate": metrics.pass_rate,
        "errored": float(metrics.errored),
        "latency.mean_ms": metrics.latency.mean_ms,
        "latency.p95_ms": metrics.latency.p95_ms,
        "tokens.total_tokens": float(metrics.tokens.total_tokens),
        "tokens.mean_tokens_per_case": metrics.tokens.mean_tokens_per_case,
    }
    for scorer_name, stats in metrics.scorers.items():
        flat[f"scorer.{scorer_name}.mean_score"] = stats.mean_score
        flat[f"scorer.{scorer_name}.pass_rate"] = stats.pass_rate
    for segment, stats in metrics.segments.items():
        for scorer_name, value in stats.scorer_means.items():
            flat[f"segment.{segment}.{scorer_name}"] = value
    return flat


def classify_metric_kind(name: str) -> MetricKind:
    """Classify a flattened metric name into a :class:`MetricKind`."""
    if name == "errored":
        return MetricKind.ERRORS
    if name.startswith("latency."):
        return MetricKind.LATENCY
    if name.startswith("tokens."):
        return MetricKind.TOKENS
    return MetricKind.QUALITY  # pass_rate, scorer.*, segment.*


class RegressionDetector:
    """Compares a candidate run to a baseline run using configurable thresholds."""

    def __init__(self, thresholds: ThresholdConfig | None = None) -> None:
        self._thresholds = thresholds or ThresholdConfig()

    def compare(self, baseline: EvaluationResult, candidate: EvaluationResult) -> RegressionResult:
        """Compare ``candidate`` against ``baseline`` and return a result."""
        if baseline.feature != candidate.feature:
            raise RegressionError(
                f"Cannot compare different features: {baseline.feature!r} vs {candidate.feature!r}"
            )

        base_flat = flatten_metrics(baseline.aggregate_metrics)
        cand_flat = flatten_metrics(candidate.aggregate_metrics)
        shared_names = sorted(set(base_flat) & set(cand_flat))

        comparisons = [
            self._compare_metric(name, base_flat[name], cand_flat[name]) for name in shared_names
        ]
        regressions = [c for c in comparisons if c.severity != Severity.PASS]
        severity = worst_severity(c.severity for c in comparisons)

        result = RegressionResult(
            feature=candidate.feature,
            baseline_run_id=baseline.run_id,
            candidate_run_id=candidate.run_id,
            baseline_prompt_version=baseline.prompt_version,
            candidate_prompt_version=candidate.prompt_version,
            baseline_dataset_version=baseline.dataset_version,
            candidate_dataset_version=candidate.dataset_version,
            prompt_changed=baseline.prompt_hash != candidate.prompt_hash,
            dataset_changed=baseline.dataset_hash != candidate.dataset_hash,
            severity=severity,
            comparisons=comparisons,
            regressions=regressions,
            warning_count=sum(1 for c in regressions if c.severity == Severity.WARNING),
            critical_count=sum(1 for c in regressions if c.severity == Severity.CRITICAL),
        )
        logger.info(
            "Regression compare %s: baseline=%s candidate=%s severity=%s regressions=%d",
            result.feature,
            result.baseline_run_id,
            result.candidate_run_id,
            result.severity.value,
            len(regressions),
        )
        return result

    # -- per-metric severity ----------------------------------------------------

    def _compare_metric(self, name: str, baseline: float, candidate: float) -> MetricComparison:
        kind = classify_metric_kind(name)
        delta = candidate - baseline
        relative_delta = delta / baseline if baseline != 0 else None

        if kind is MetricKind.QUALITY:
            severity, reason = self._quality_severity(name, baseline, candidate)
        elif kind is MetricKind.ERRORS:
            severity, reason = self._error_severity(baseline, candidate)
        else:  # LATENCY or TOKENS — both lower-is-better, relative increase
            increase = (
                self._thresholds.latency if kind is MetricKind.LATENCY else self._thresholds.tokens
            )
            severity, reason = self._increase_severity(
                baseline, candidate, increase.warning_rel_increase, increase.critical_rel_increase
            )

        return MetricComparison(
            name=name,
            kind=kind,
            baseline_value=baseline,
            candidate_value=candidate,
            delta=delta,
            relative_delta=relative_delta,
            severity=severity,
            regressed=severity != Severity.PASS,
            reason=reason,
        )

    def _quality_severity(
        self, name: str, baseline: float, candidate: float
    ) -> tuple[Severity, str]:
        th = self._thresholds.per_metric.get(name, self._thresholds.quality)
        drop = baseline - candidate
        if drop <= 0:
            return Severity.PASS, "no drop"
        rel_drop = drop / baseline if baseline > 0 else None
        if drop >= th.critical_abs_drop or (
            rel_drop is not None and rel_drop >= th.critical_rel_drop
        ):
            return Severity.CRITICAL, self._drop_reason(drop, rel_drop)
        warn_by_rel = rel_drop is not None and rel_drop >= th.warning_rel_drop
        if drop >= th.warning_abs_drop or warn_by_rel:
            return Severity.WARNING, self._drop_reason(drop, rel_drop)
        return Severity.PASS, self._drop_reason(drop, rel_drop)

    def _increase_severity(
        self, baseline: float, candidate: float, warn_rel: float, crit_rel: float
    ) -> tuple[Severity, str]:
        increase = candidate - baseline
        if increase <= 0:
            return Severity.PASS, "no increase"
        if baseline <= 0:
            return Severity.PASS, "baseline is zero; relative increase undefined"
        rel = increase / baseline
        if rel >= crit_rel:
            return Severity.CRITICAL, f"increased {increase:.4g} ({rel:.1%})"
        if rel >= warn_rel:
            return Severity.WARNING, f"increased {increase:.4g} ({rel:.1%})"
        return Severity.PASS, f"increased {increase:.4g} ({rel:.1%})"

    def _error_severity(self, baseline: float, candidate: float) -> tuple[Severity, str]:
        increase = candidate - baseline
        if increase <= 0:
            return Severity.PASS, "no new errors"
        th = self._thresholds.errors
        if increase >= th.critical_increase:
            return Severity.CRITICAL, f"errored +{int(increase)}"
        if increase >= th.warning_increase:
            return Severity.WARNING, f"errored +{int(increase)}"
        return Severity.PASS, f"errored +{int(increase)}"

    @staticmethod
    def _drop_reason(drop: float, rel_drop: float | None) -> str:
        rel = f" ({rel_drop:.1%})" if rel_drop is not None else ""
        return f"dropped {drop:.4g}{rel}"
