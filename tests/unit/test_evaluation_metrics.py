"""Unit tests for pure metric aggregation."""

from __future__ import annotations

import pytest

from mrds.core.interfaces import ScoreResult
from mrds.datasets.models import Difficulty
from mrds.evaluation.metrics import _percentile, aggregate
from mrds.evaluation.models import CaseResult


def _case(
    case_id: str,
    *,
    category: str,
    cat_pass: bool,
    sum_pass: bool = True,
    latency: float = 10.0,
    tokens: int = 5,
    error: str | None = None,
) -> CaseResult:
    scores = (
        []
        if error
        else [
            ScoreResult(name="category_match", score=1.0 if cat_pass else 0.0, passed=cat_pass),
            ScoreResult(name="summary_quality", score=1.0 if sum_pass else 0.0, passed=sum_pass),
        ]
    )
    passed = error is None and cat_pass and sum_pass
    return CaseResult(
        case_id=case_id,
        expected_difficulty=Difficulty.EASY,
        input={"email_text": "x"},
        expected_output={"category": category, "summary": "s"},
        actual_output=None if error else {"category": category, "summary": "s"},
        scores=scores,
        passed=passed,
        latency_ms=latency,
        input_tokens=tokens,
        output_tokens=tokens,
        total_tokens=tokens * 2,
        error=error,
    )


def test_pass_fail_error_counts() -> None:
    cases = [
        _case("a", category="billing", cat_pass=True),
        _case("b", category="billing", cat_pass=False),
        _case("c", category="account", cat_pass=True, sum_pass=False),
        _case("d", category="account", cat_pass=True, error="boom"),
    ]
    m = aggregate(cases, scorer_names=["category_match", "summary_quality"])
    assert m.total_cases == 4
    assert m.passed == 1
    assert m.errored == 1
    assert m.failed == 2
    assert m.pass_rate == pytest.approx(0.25)


def test_scorer_means_and_pass_rates() -> None:
    cases = [
        _case("a", category="billing", cat_pass=True),
        _case("b", category="billing", cat_pass=False),
    ]
    m = aggregate(cases, scorer_names=["category_match", "summary_quality"])
    # category accuracy = mean of category_match
    assert m.scorers["category_match"].mean_score == pytest.approx(0.5)
    assert m.scorers["category_match"].pass_rate == pytest.approx(0.5)
    assert m.scorers["summary_quality"].mean_score == pytest.approx(1.0)


def test_per_segment_metrics() -> None:
    cases = [
        _case("a", category="billing", cat_pass=True),
        _case("b", category="billing", cat_pass=False),
        _case("c", category="account", cat_pass=True),
    ]
    m = aggregate(cases, scorer_names=["category_match"], segment_field="category")
    assert set(m.segments) == {"billing", "account"}
    assert m.segments["billing"].scorer_means["category_match"] == pytest.approx(0.5)
    assert m.segments["account"].pass_rate == pytest.approx(1.0)


def test_latency_and_token_stats() -> None:
    cases = [
        _case("a", category="billing", cat_pass=True, latency=10.0, tokens=5),
        _case("b", category="billing", cat_pass=True, latency=20.0, tokens=5),
        _case("c", category="billing", cat_pass=True, latency=30.0, tokens=5),
    ]
    m = aggregate(cases, scorer_names=["category_match"])
    assert m.latency.min_ms == 10.0
    assert m.latency.max_ms == 30.0
    assert m.latency.mean_ms == pytest.approx(20.0)
    assert m.latency.p50_ms == pytest.approx(20.0)
    assert m.tokens.total_tokens == 30  # 3 cases * (5 + 5)
    assert m.tokens.mean_tokens_per_case == pytest.approx(10.0)


def test_percentile_helper() -> None:
    assert _percentile([], 0.5) == 0.0
    assert _percentile([42.0], 0.95) == 42.0
    assert _percentile([10.0, 20.0, 30.0, 40.0], 0.5) == pytest.approx(25.0)


def test_empty_run_is_safe() -> None:
    m = aggregate([], scorer_names=["category_match"])
    assert m.total_cases == 0
    assert m.pass_rate == 0.0
    assert m.scorers["category_match"].count == 0
