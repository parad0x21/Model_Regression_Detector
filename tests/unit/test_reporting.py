"""Tests for the reporting system (rendering, templates, evaluation + regression)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from jinja2 import PackageLoader
from jinja2.exceptions import TemplateNotFound

from mrds.core.interfaces import ScoreResult
from mrds.datasets.models import Difficulty
from mrds.evaluation.models import (
    AggregateMetrics,
    CaseResult,
    EvaluationResult,
    LatencyStats,
    ScorerStats,
    SegmentStats,
    TokenStats,
)
from mrds.regression import BaselineCandidate, BaselinePromoter, RegressionDetector
from mrds.regression.models import Baseline
from mrds.reporting import ReportBuilder, ReportFormat, save_report
from mrds.reporting.builder import _is_improvement

NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=UTC)


def _result(
    run_id: str,
    *,
    feature: str = "email_classifier",
    prompt: str = "v1",
    prompt_hash: str = "ph1234567890ab",
    dataset: str = "v1",
    dataset_hash: str = "dh1234567890ab",
    pass_rate: float = 0.9,
    scorers: dict[str, float] | None = None,
    segments: dict[str, dict[str, float]] | None = None,
    errored: int = 0,
    lat_mean: float = 12.0,
    tok_mean: float = 10.0,
    with_cases: bool = True,
) -> EvaluationResult:
    scorers = scorers or {"category_match": 0.9, "summary_quality": 1.0}
    segments = segments or {"billing": {"category_match": 0.85}, "general": {"category_match": 1.0}}
    cases = (
        [
            CaseResult(
                case_id="ec-001",
                expected_difficulty=Difficulty.EASY,
                input={"email_text": "I was charged twice."},
                expected_output={"category": "billing", "summary": "Double charge."},
                actual_output={"category": "billing", "summary": "Double charge."},
                scores=[
                    ScoreResult(name="category_match", score=1.0, passed=True),
                    ScoreResult(name="summary_quality", score=1.0, passed=True),
                ],
                passed=True,
                latency_ms=11.0,
                total_tokens=20,
            ),
            CaseResult(
                case_id="ec-002",
                expected_difficulty=Difficulty.HARD,
                input={"email_text": "It's broken."},
                expected_output={"category": "technical", "summary": "Something broke."},
                actual_output=None,
                scores=[],
                passed=False,
                latency_ms=9.0,
                error="LLM failed",
            ),
        ]
        if with_cases
        else []
    )
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
        duration_seconds=1.5,
        aggregate_metrics=AggregateMetrics(
            total_cases=10,
            passed=int(pass_rate * 10),
            failed=10 - int(pass_rate * 10) - errored,
            errored=errored,
            pass_rate=pass_rate,
            scorers={
                n: ScorerStats(name=n, mean_score=v, pass_rate=v, passed=int(v * 10), count=10)
                for n, v in scorers.items()
            },
            segments={
                s: SegmentStats(segment=s, count=5, passed=4, pass_rate=0.8, scorer_means=m)
                for s, m in segments.items()
            },
            segment_field="category",
            latency=LatencyStats(
                count=10,
                total_ms=lat_mean * 10,
                mean_ms=lat_mean,
                min_ms=lat_mean,
                p50_ms=lat_mean,
                p95_ms=lat_mean + 5,
                max_ms=lat_mean + 8,
            ),
            tokens=TokenStats(
                total_tokens=int(tok_mean * 10),
                total_input_tokens=int(tok_mean * 6),
                total_output_tokens=int(tok_mean * 4),
                mean_tokens_per_case=tok_mean,
            ),
        ),
        per_case_results=cases,
    )


# -- template validation --------------------------------------------------------


def test_all_templates_parse() -> None:
    loader = PackageLoader("mrds.reporting", "templates")
    expected = {
        "evaluation_report.html.j2",
        "regression_report.html.j2",
        "evaluation_summary.md.j2",
        "regression_summary.md.j2",
    }
    available = set(loader.list_templates())
    assert expected <= available
    builder = ReportBuilder()
    for name in expected:
        builder._env.get_template(name)  # parses or raises


# -- evaluation report ----------------------------------------------------------


def test_evaluation_html_report() -> None:
    report = ReportBuilder().render_evaluation(_result("run-eval-1"), ReportFormat.HTML)
    html = report.content
    assert report.format is ReportFormat.HTML
    assert html.startswith("<!DOCTYPE html>") and "</html>" in html
    # Required sections / dynamic content.
    for token in [
        "Run metadata",
        "Aggregate metrics",
        "Scorer metrics",
        "Segment metrics",
        "Token usage",
        "Latency statistics",
        "Per-case summary",
        "email_classifier",
        "run-eval-1",
        "category_match",
        "summary_quality",
        "billing",
        "ec-001",
        "ec-002",
    ]:
        assert token in html, token
    assert "90.0%" in html  # pass rate


def test_evaluation_markdown_report() -> None:
    report = ReportBuilder().render_evaluation(_result("run-eval-2"), ReportFormat.MARKDOWN)
    md = report.content
    assert report.format is ReportFormat.MARKDOWN
    assert md.startswith("# Evaluation Report")
    assert "## Aggregate" in md
    assert "## Scorers" in md
    assert "category_match" in md
    assert "## Segments (by category)" in md


def test_html_escaping_applies_to_html_only() -> None:
    result = _result("run-x", scorers={"a<b>": 0.9})
    html = ReportBuilder().render_evaluation(result, ReportFormat.HTML).content
    md = ReportBuilder().render_evaluation(result, ReportFormat.MARKDOWN).content
    assert "a&lt;b&gt;" in html  # escaped in HTML
    assert "a<b>" in md  # not escaped in Markdown


# -- regression report ----------------------------------------------------------


def _regression(eligibility: bool = True):
    baseline_result = _result(
        "base-1", pass_rate=0.92, scorers={"category_match": 0.92, "summary_quality": 1.0}
    )
    candidate_result = _result(
        "cand-1",
        prompt="v2",
        prompt_hash="ph_v2_xxxxxxx",
        pass_rate=0.80,
        scorers={"category_match": 0.80, "summary_quality": 1.0},
        lat_mean=12.0,
    )
    regression = RegressionDetector().compare(baseline_result, candidate_result)
    promoter = BaselinePromoter()
    current = Baseline(
        feature="email_classifier", result=baseline_result, promoted_at=NOW, promoted_by="t"
    )
    elig = None
    if eligibility:
        elig = promoter.check(BaselineCandidate(result=candidate_result), current)
    return regression, elig


def test_regression_html_report() -> None:
    regression, elig = _regression()
    report = ReportBuilder().render_regression(regression, eligibility=elig, fmt=ReportFormat.HTML)
    html = report.content
    assert html.startswith("<!DOCTYPE html>")
    for token in [
        "Severity:",
        "CRITICAL",
        "DEPLOYMENT BLOCKED",
        "base-1",
        "cand-1",
        "Regressed metrics",
        "Improved metrics",
        "Promotion status",
        "scorer.category_match.mean_score",
    ]:
        assert token in html, token


def test_regression_markdown_report() -> None:
    regression, elig = _regression()
    report = ReportBuilder().render_regression(
        regression, eligibility=elig, fmt=ReportFormat.MARKDOWN
    )
    md = report.content
    assert md.startswith("# Regression Report")
    assert "CRITICAL" in md
    assert "## Regressed metrics" in md
    assert "## Promotion" in md
    assert "scorer.category_match.mean_score" in md


def test_regression_without_promotion_section() -> None:
    regression, _ = _regression(eligibility=False)
    html = ReportBuilder().render_regression(regression, fmt=ReportFormat.HTML).content
    assert "Promotion not evaluated." in html


def test_improved_vs_regressed_split() -> None:
    # category_match drops (regressed); pass_rate improves (improved).
    baseline = _result("b", pass_rate=0.80, scorers={"category_match": 0.95})
    candidate = _result("c", pass_rate=0.90, scorers={"category_match": 0.70})
    regression = RegressionDetector().compare(baseline, candidate)
    ctx = ReportBuilder().build_regression_context(regression)
    regressed_names = {m.name for m in ctx.regressed}
    improved_names = {m.name for m in ctx.improved}
    assert "scorer.category_match.mean_score" in regressed_names
    assert "pass_rate" in improved_names


def test_is_improvement_direction() -> None:
    from mrds.regression.models import MetricComparison, MetricKind, Severity

    quality_up = MetricComparison(
        name="x",
        kind=MetricKind.QUALITY,
        baseline_value=0.8,
        candidate_value=0.9,
        delta=0.1,
        relative_delta=0.125,
        severity=Severity.PASS,
        regressed=False,
        reason="",
    )
    latency_up = MetricComparison(
        name="latency.mean_ms",
        kind=MetricKind.LATENCY,
        baseline_value=10,
        candidate_value=20,
        delta=10,
        relative_delta=1.0,
        severity=Severity.CRITICAL,
        regressed=True,
        reason="",
    )
    assert _is_improvement(quality_up) is True
    assert _is_improvement(latency_up) is False  # latency up is worse


# -- feature-agnostic + IO ------------------------------------------------------


def test_reporting_is_feature_agnostic() -> None:
    result = _result(
        "rag-1",
        feature="rag_qa",
        scorers={"answer_relevance": 0.88, "faithfulness": 0.91},
        segments={"easy": {"answer_relevance": 0.95}, "hard": {"answer_relevance": 0.6}},
    )
    html = ReportBuilder().render_evaluation(result, ReportFormat.HTML).content
    assert "rag_qa" in html
    assert "answer_relevance" in html
    assert "faithfulness" in html


def test_save_report_writes_file(tmp_path) -> None:
    report = ReportBuilder().render_evaluation(_result("run-save"), ReportFormat.MARKDOWN)
    path = save_report(report, tmp_path / "sub" / "report.md")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == report.content


def test_unknown_scorer_count_safe() -> None:
    # A run with no segmentation still renders.
    result = _result("run-noseg", segments={})
    result = result.model_copy(
        update={
            "aggregate_metrics": result.aggregate_metrics.model_copy(
                update={"segments": {}, "segment_field": None}
            )
        }
    )
    html = ReportBuilder().render_evaluation(result, ReportFormat.HTML).content
    assert "No segmentation configured." in html
    with pytest.raises(TemplateNotFound):
        ReportBuilder()._env.get_template("does_not_exist.j2")
