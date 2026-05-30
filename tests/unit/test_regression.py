"""Tests for the regression-detection system and baseline-promotion workflow."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mrds.evaluation.models import (
    AggregateMetrics,
    EvaluationResult,
    LatencyStats,
    ScorerStats,
    SegmentStats,
    TokenStats,
)
from mrds.regression import (
    Baseline,
    BaselineCandidate,
    BaselinePromoter,
    MetricKind,
    PromotionNotEligibleError,
    QualityThresholds,
    RegressionDetector,
    RegressionError,
    Severity,
    ThresholdConfig,
    classify_metric_kind,
    flatten_metrics,
)

NOW = datetime(2026, 5, 29, tzinfo=UTC)


def _agg(
    *,
    pass_rate: float,
    scorers: dict[str, float],
    segments: dict[str, dict[str, float]] | None = None,
    errored: int = 0,
    lat_mean: float = 10.0,
    lat_p95: float = 12.0,
    tok_total: int = 100,
    tok_mean: float = 10.0,
) -> AggregateMetrics:
    return AggregateMetrics(
        total_cases=10,
        passed=int(pass_rate * 10),
        failed=10 - int(pass_rate * 10),
        errored=errored,
        pass_rate=pass_rate,
        scorers={
            name: ScorerStats(name=name, mean_score=val, pass_rate=val, passed=0, count=10)
            for name, val in scorers.items()
        },
        segments={
            seg: SegmentStats(segment=seg, count=5, passed=0, pass_rate=0.0, scorer_means=means)
            for seg, means in (segments or {}).items()
        },
        segment_field="category" if segments else None,
        latency=LatencyStats(
            count=10,
            total_ms=lat_mean * 10,
            mean_ms=lat_mean,
            min_ms=lat_mean,
            p50_ms=lat_mean,
            p95_ms=lat_p95,
            max_ms=lat_p95,
        ),
        tokens=TokenStats(
            total_tokens=tok_total,
            total_input_tokens=0,
            total_output_tokens=0,
            mean_tokens_per_case=tok_mean,
        ),
    )


def _result(
    run_id: str,
    *,
    feature: str = "email_classifier",
    prompt: str = "v1",
    prompt_hash: str = "ph1",
    dataset: str = "v1",
    dataset_hash: str = "dh1",
    **agg_kwargs: object,
) -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        feature=feature,
        prompt_version=prompt,
        prompt_hash=prompt_hash,
        dataset_version=dataset,
        dataset_hash=dataset_hash,
        model="gpt-4o-mini",
        start_time=NOW,
        end_time=NOW,
        duration_seconds=1.0,
        aggregate_metrics=_agg(**agg_kwargs),  # type: ignore[arg-type]
        per_case_results=[],
    )


# -- flatten / discovery --------------------------------------------------------


def test_flatten_discovers_metric_names_dynamically() -> None:
    agg = _agg(
        pass_rate=0.9,
        scorers={"category_match": 0.9, "summary_quality": 1.0},
        segments={"billing": {"category_match": 0.8}},
    )
    flat = flatten_metrics(agg)
    assert flat["pass_rate"] == 0.9
    assert flat["scorer.category_match.mean_score"] == 0.9
    assert flat["scorer.summary_quality.pass_rate"] == 1.0
    assert flat["segment.billing.category_match"] == 0.8
    assert "latency.p95_ms" in flat and "tokens.total_tokens" in flat


def test_metric_kind_classification() -> None:
    assert classify_metric_kind("pass_rate") is MetricKind.QUALITY
    assert classify_metric_kind("scorer.x.mean_score") is MetricKind.QUALITY
    assert classify_metric_kind("segment.a.x") is MetricKind.QUALITY
    assert classify_metric_kind("latency.mean_ms") is MetricKind.LATENCY
    assert classify_metric_kind("tokens.total_tokens") is MetricKind.TOKENS
    assert classify_metric_kind("errored") is MetricKind.ERRORS


# -- comparison / severity ------------------------------------------------------


def test_identical_runs_have_no_regression() -> None:
    base = _result("b", pass_rate=0.9, scorers={"category_match": 0.9})
    cand = _result("c", pass_rate=0.9, scorers={"category_match": 0.9})
    result = RegressionDetector().compare(base, cand)
    assert result.severity is Severity.PASS
    assert not result.has_regression
    assert not result.is_blocking
    assert result.regressions == []


def test_small_quality_drop_is_warning() -> None:
    base = _result("b", pass_rate=0.90, scorers={"category_match": 0.90})
    cand = _result("c", pass_rate=0.87, scorers={"category_match": 0.87})  # -0.03 abs
    result = RegressionDetector().compare(base, cand)
    assert result.severity is Severity.WARNING
    assert result.warning_count >= 1


def test_large_quality_drop_is_critical_and_blocking() -> None:
    base = _result("b", pass_rate=0.90, scorers={"category_match": 0.90})
    cand = _result("c", pass_rate=0.80, scorers={"category_match": 0.80})  # -0.10 abs
    result = RegressionDetector().compare(base, cand)
    assert result.severity is Severity.CRITICAL
    assert result.is_blocking
    assert result.critical_count >= 1


def test_improvement_is_not_a_regression() -> None:
    base = _result("b", pass_rate=0.80, scorers={"category_match": 0.80})
    cand = _result("c", pass_rate=0.95, scorers={"category_match": 0.95})
    result = RegressionDetector().compare(base, cand)
    assert result.severity is Severity.PASS


def test_relative_drop_threshold() -> None:
    # 0.40 -> 0.36 is only -0.04 absolute (below 0.05 critical abs) but -10% relative.
    base = _result("b", pass_rate=0.40, scorers={"category_match": 0.40})
    cand = _result("c", pass_rate=0.40, scorers={"category_match": 0.36})
    result = RegressionDetector().compare(base, cand)
    comp = next(c for c in result.comparisons if c.name == "scorer.category_match.mean_score")
    assert comp.relative_delta == pytest.approx(-0.10)
    assert comp.severity is Severity.CRITICAL  # 10% rel >= critical_rel_drop default


def test_latency_increase_thresholds() -> None:
    base = _result("b", pass_rate=0.9, scorers={"category_match": 0.9}, lat_mean=100.0)
    cand = _result("c", pass_rate=0.9, scorers={"category_match": 0.9}, lat_mean=160.0)  # +60%
    result = RegressionDetector().compare(base, cand)
    comp = next(c for c in result.comparisons if c.name == "latency.mean_ms")
    assert comp.kind is MetricKind.LATENCY
    assert comp.severity is Severity.CRITICAL  # >50%


def test_token_increase_thresholds() -> None:
    base = _result("b", pass_rate=0.9, scorers={"category_match": 0.9}, tok_mean=100.0)
    cand = _result("c", pass_rate=0.9, scorers={"category_match": 0.9}, tok_mean=130.0)  # +30%
    result = RegressionDetector().compare(base, cand)
    comp = next(c for c in result.comparisons if c.name == "tokens.mean_tokens_per_case")
    assert comp.severity is Severity.WARNING  # >25% but <50%


def test_error_increase_thresholds() -> None:
    base = _result("b", pass_rate=0.9, scorers={"category_match": 0.9}, errored=0)
    cand = _result("c", pass_rate=0.9, scorers={"category_match": 0.9}, errored=4)
    result = RegressionDetector().compare(base, cand)
    comp = next(c for c in result.comparisons if c.name == "errored")
    assert comp.kind is MetricKind.ERRORS
    assert comp.severity is Severity.CRITICAL  # +4 >= critical_increase (3)


def test_per_metric_threshold_override() -> None:
    thresholds = ThresholdConfig(
        per_metric={
            "scorer.category_match.mean_score": QualityThresholds(
                warning_abs_drop=0.001, critical_abs_drop=0.5
            )
        }
    )
    base = _result("b", pass_rate=0.9, scorers={"category_match": 0.90})
    cand = _result("c", pass_rate=0.9, scorers={"category_match": 0.89})  # tiny -0.01 drop
    result = RegressionDetector(thresholds).compare(base, cand)
    comp = next(c for c in result.comparisons if c.name == "scorer.category_match.mean_score")
    assert comp.severity is Severity.WARNING  # tightened threshold triggers


def test_overall_severity_is_worst_metric() -> None:
    # category_match critical drop, summary_quality fine -> overall CRITICAL.
    base = _result("b", pass_rate=0.9, scorers={"category_match": 0.9, "summary_quality": 1.0})
    cand = _result("c", pass_rate=0.9, scorers={"category_match": 0.7, "summary_quality": 1.0})
    result = RegressionDetector().compare(base, cand)
    assert result.severity is Severity.CRITICAL


def test_compare_rejects_feature_mismatch() -> None:
    base = _result("b", feature="email_classifier", pass_rate=0.9, scorers={"x": 0.9})
    cand = _result("c", feature="rag_qa", pass_rate=0.9, scorers={"x": 0.9})
    with pytest.raises(RegressionError):
        RegressionDetector().compare(base, cand)


def test_prompt_and_dataset_change_flags() -> None:
    base = _result("b", pass_rate=0.9, scorers={"x": 0.9}, prompt_hash="h1", dataset_hash="d1")
    cand = _result(
        "c", pass_rate=0.9, scorers={"x": 0.9}, prompt="v2", prompt_hash="h2", dataset_hash="d1"
    )
    result = RegressionDetector().compare(base, cand)
    assert result.prompt_changed is True
    assert result.dataset_changed is False


# -- feature-agnostic -----------------------------------------------------------


def test_detector_is_feature_agnostic() -> None:
    # An entirely different feature with its own scorer/segment names.
    base = _result(
        "b",
        feature="rag_qa",
        pass_rate=0.80,
        scorers={"answer_relevance": 0.80, "faithfulness": 0.90},
        segments={"easy": {"answer_relevance": 0.95}, "hard": {"answer_relevance": 0.60}},
    )
    cand = _result(
        "c",
        feature="rag_qa",
        pass_rate=0.80,
        scorers={"answer_relevance": 0.60, "faithfulness": 0.90},
        segments={"easy": {"answer_relevance": 0.95}, "hard": {"answer_relevance": 0.40}},
    )
    result = RegressionDetector().compare(base, cand)
    names = {c.name for c in result.comparisons}
    assert "scorer.answer_relevance.mean_score" in names
    assert "segment.hard.answer_relevance" in names
    assert result.is_blocking  # answer_relevance dropped 0.20


# -- baseline promotion ---------------------------------------------------------


def _candidate(run_id: str, **kwargs: object) -> BaselineCandidate:
    return BaselineCandidate(result=_result(run_id, **kwargs))  # type: ignore[arg-type]


def _baseline(run_id: str, **kwargs: object) -> Baseline:
    return Baseline(
        feature=kwargs.get("feature", "email_classifier"),  # type: ignore[arg-type]
        result=_result(run_id, **kwargs),  # type: ignore[arg-type]
        promoted_at=NOW,
        promoted_by="tester",
    )


def test_first_promotion_is_eligible() -> None:
    promoter = BaselinePromoter()
    candidate = _candidate("c", pass_rate=0.9, scorers={"category_match": 0.9})
    eligibility = promoter.check(candidate, current=None)
    assert eligibility.eligible
    baseline = promoter.promote(candidate, current=None, promoted_by="ci", note="first")
    assert baseline.run_id == "c"
    assert baseline.promoted_by == "ci"


def test_promotion_blocked_on_critical_regression() -> None:
    promoter = BaselinePromoter()
    current = _baseline("b", pass_rate=0.9, scorers={"category_match": 0.9})
    candidate = _candidate("c", pass_rate=0.75, scorers={"category_match": 0.75})
    eligibility = promoter.check(candidate, current)
    assert not eligibility.eligible
    assert eligibility.severity is Severity.CRITICAL
    with pytest.raises(PromotionNotEligibleError):
        promoter.promote(candidate, current=current)


def test_promotion_force_overrides_ineligibility() -> None:
    promoter = BaselinePromoter()
    current = _baseline("b", pass_rate=0.9, scorers={"category_match": 0.9})
    candidate = _candidate("c", pass_rate=0.75, scorers={"category_match": 0.75})
    baseline = promoter.promote(candidate, current=current, force=True)
    assert baseline.run_id == "c"


def test_promotion_warning_allowed_by_default_but_configurable() -> None:
    current = _baseline("b", pass_rate=0.90, scorers={"category_match": 0.90})
    candidate = _candidate("c", pass_rate=0.87, scorers={"category_match": 0.87})  # warning drop

    assert BaselinePromoter(allow_warnings=True).check(candidate, current).eligible
    strict = BaselinePromoter(allow_warnings=False).check(candidate, current)
    assert not strict.eligible
    assert strict.severity is Severity.WARNING


def test_promotion_blocked_on_feature_mismatch() -> None:
    promoter = BaselinePromoter()
    current = _baseline("b", feature="email_classifier", pass_rate=0.9, scorers={"x": 0.9})
    candidate = _candidate("c", feature="rag_qa", pass_rate=0.9, scorers={"x": 0.9})
    eligibility = promoter.check(candidate, current)
    assert not eligibility.eligible
    assert "mismatch" in eligibility.reasons[0].lower()
