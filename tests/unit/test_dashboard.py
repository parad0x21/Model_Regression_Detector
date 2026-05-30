"""Tests for the dashboard data-access layer and its repository integration."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mrds.core.interfaces import ScoreResult
from mrds.dashboard.data import DashboardData, TrendPoint
from mrds.datasets.models import Difficulty
from mrds.db import EvaluationStore, open_database
from mrds.evaluation.models import (
    AggregateMetrics,
    CaseResult,
    EvaluationResult,
    LatencyStats,
    ScorerStats,
    TokenStats,
)
from mrds.regression import RegressionDetector

NOW = datetime(2026, 5, 30, 12, 0, 0, tzinfo=UTC)


def _result(
    run_id: str, *, feature: str = "email_classifier", cat_mean: float, pass_rate: float
) -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        feature=feature,
        prompt_version="v1",
        prompt_hash="ph1",
        dataset_version="v1",
        dataset_hash="dh1",
        model="gpt-4o-mini",
        start_time=NOW,
        end_time=NOW,
        duration_seconds=1.0,
        aggregate_metrics=AggregateMetrics(
            total_cases=10,
            passed=int(pass_rate * 10),
            failed=10 - int(pass_rate * 10),
            errored=0,
            pass_rate=pass_rate,
            scorers={
                "category_match": ScorerStats(
                    name="category_match",
                    mean_score=cat_mean,
                    pass_rate=cat_mean,
                    passed=9,
                    count=10,
                )
            },
            segments={},
            segment_field=None,
            latency=LatencyStats(
                count=10, total_ms=120, mean_ms=12, min_ms=9, p50_ms=11, p95_ms=20, max_ms=25
            ),
            tokens=TokenStats(
                total_tokens=120,
                total_input_tokens=80,
                total_output_tokens=40,
                mean_tokens_per_case=12.0,
            ),
        ),
        per_case_results=[
            CaseResult(
                case_id="c-1",
                expected_difficulty=Difficulty.EASY,
                input={"email_text": "hi"},
                expected_output={"category": "billing", "summary": "x"},
                actual_output={"category": "billing", "summary": "x"},
                scores=[ScoreResult(name="category_match", score=cat_mean, passed=True)],
                passed=True,
                latency_ms=10.0,
                total_tokens=12,
            )
        ],
    )


@pytest.fixture
def data() -> DashboardData:
    store = EvaluationStore(open_database(":memory:"))
    # Two runs for email_classifier + one for a second feature.
    store.save_evaluation(_result("run-1", cat_mean=0.95, pass_rate=0.95))
    store.save_evaluation(_result("run-2", cat_mean=0.80, pass_rate=0.80))
    store.save_evaluation(_result("rag-1", feature="rag_qa", cat_mean=0.9, pass_rate=0.9))
    # A regression for run-2 against promoted run-1.
    store.promote_baseline("run-1", promoted_by="ci", note="first baseline")
    regression = RegressionDetector().compare(
        store.get_evaluation_result("run-1"), store.get_evaluation_result("run-2")
    )
    store.save_regression(regression)
    return DashboardData(store)


# -- features / runs ------------------------------------------------------------


def test_features_are_distinct_and_sorted(data: DashboardData) -> None:
    assert data.features() == ["email_classifier", "rag_qa"]


def test_runs_lists_most_recent_first(data: DashboardData) -> None:
    runs = data.runs("email_classifier")
    assert [r.run_uuid for r in runs] == ["run-2", "run-1"]


def test_run_detail_reconstructs(data: DashboardData) -> None:
    result = data.run_detail("run-1")
    assert result is not None
    assert result.feature == "email_classifier"
    assert result.aggregate_metrics.pass_rate == pytest.approx(0.95)
    assert result.per_case_results[0].case_id == "c-1"


def test_run_detail_unknown_returns_none(data: DashboardData) -> None:
    assert data.run_detail("missing") is None


# -- trends ---------------------------------------------------------------------


def test_trend_is_chronological(data: DashboardData) -> None:
    points = data.trend("email_classifier")
    assert [p.run_uuid for p in points] == ["run-1", "run-2"]  # oldest -> newest
    assert isinstance(points[0], TrendPoint)
    assert points[0].pass_rate == pytest.approx(0.95)
    assert points[1].pass_rate == pytest.approx(0.80)
    assert points[0].scorer_means["category_match"] == pytest.approx(0.95)
    assert points[0].mean_latency_ms == 12.0
    assert points[0].total_tokens == 120


def test_trend_empty_for_unknown_feature(data: DashboardData) -> None:
    assert data.trend("nope") == []


# -- regressions ----------------------------------------------------------------


def test_regressions_for_run(data: DashboardData) -> None:
    regressions = data.regressions_for_run("run-2")
    assert regressions
    assert any(r.metric == "scorer.category_match.mean_score" for r in regressions)
    assert all(r.severity in {"warning", "critical"} for r in regressions)


def test_regressions_for_run_without_regressions(data: DashboardData) -> None:
    assert data.regressions_for_run("run-1") == []


def test_regressions_for_unknown_run(data: DashboardData) -> None:
    assert data.regressions_for_run("missing") == []


# -- baselines ------------------------------------------------------------------


def test_active_baseline_and_history(data: DashboardData) -> None:
    active = data.active_baseline("email_classifier")
    assert active is not None
    assert data.run_uuid_for(active.run_id) == "run-1"
    assert len(data.baseline_history("email_classifier")) == 1


def test_no_baseline_for_other_feature(data: DashboardData) -> None:
    assert data.active_baseline("rag_qa") is None


# -- repository integration -----------------------------------------------------


def test_run_repository_features_distinct(data: DashboardData) -> None:
    store = EvaluationStore(open_database(":memory:"))
    assert store.runs.features() == []
    store.save_evaluation(_result("a", cat_mean=0.9, pass_rate=0.9))
    store.save_evaluation(_result("b", cat_mean=0.9, pass_rate=0.9))
    assert store.runs.features() == ["email_classifier"]  # distinct
