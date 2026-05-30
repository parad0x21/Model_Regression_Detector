"""Report builder — turns domain objects into rendered HTML/Markdown reports.

All report *logic* lives here (selecting fields, splitting regressed vs improved
metrics, deriving display context); the Jinja2 templates only render context. The
builder is feature-agnostic: it iterates scorers/segments/metrics dynamically.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader

from mrds.evaluation.models import EvaluationResult
from mrds.observability.logging import get_logger
from mrds.regression.models import (
    MetricComparison,
    MetricKind,
    PromotionEligibility,
    RegressionResult,
)
from mrds.reporting.models import (
    EvaluationReportContext,
    PromotionStatus,
    RegressionReportContext,
    RenderedReport,
    ReportFormat,
)

logger = get_logger(__name__)

_TEMPLATES = {
    ("evaluation", ReportFormat.HTML): "evaluation_report.html.j2",
    ("evaluation", ReportFormat.MARKDOWN): "evaluation_summary.md.j2",
    ("regression", ReportFormat.HTML): "regression_report.html.j2",
    ("regression", ReportFormat.MARKDOWN): "regression_summary.md.j2",
}


def _autoescape(template_name: str | None) -> bool:
    """Autoescape HTML templates only; Markdown is emitted verbatim."""
    return bool(template_name) and template_name.endswith(".html.j2")


def _is_improvement(comparison: MetricComparison) -> bool:
    """True if a metric moved in the better direction (by its kind)."""
    if comparison.delta == 0:
        return False
    if comparison.kind is MetricKind.QUALITY:
        return comparison.delta > 0  # higher is better
    return comparison.delta < 0  # latency/tokens/errors: lower is better


class ReportBuilder:
    """Builds evaluation and regression reports in HTML or Markdown."""

    def __init__(self, environment: Environment | None = None) -> None:
        self._env = environment or Environment(
            loader=PackageLoader("mrds.reporting", "templates"),
            autoescape=_autoescape,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # -- context builders -------------------------------------------------------

    def build_evaluation_context(self, result: EvaluationResult) -> EvaluationReportContext:
        """Derive template context from an :class:`EvaluationResult`."""
        agg = result.aggregate_metrics
        return EvaluationReportContext(
            title=f"Evaluation Report — {result.feature} ({result.run_id[:8]})",
            generated_at=datetime.now(UTC),
            feature=result.feature,
            run_id=result.run_id,
            model=result.model,
            prompt_version=result.prompt_version,
            prompt_hash=result.prompt_hash,
            dataset_version=result.dataset_version,
            dataset_hash=result.dataset_hash,
            start_time=result.start_time,
            end_time=result.end_time,
            duration_seconds=result.duration_seconds,
            total_cases=agg.total_cases,
            passed=agg.passed,
            failed=agg.failed,
            errored=agg.errored,
            pass_rate=agg.pass_rate,
            scorers=list(agg.scorers.values()),
            segments=list(agg.segments.values()),
            segment_field=agg.segment_field,
            latency=agg.latency,
            tokens=agg.tokens,
            cases=list(result.per_case_results),
        )

    def build_regression_context(
        self,
        regression: RegressionResult,
        *,
        eligibility: PromotionEligibility | None = None,
    ) -> RegressionReportContext:
        """Derive template context from a :class:`RegressionResult`."""
        improved = [c for c in regression.comparisons if _is_improvement(c)]
        unchanged = len(regression.comparisons) - len(regression.regressions) - len(improved)

        promotion: PromotionStatus | None = None
        if eligibility is not None:
            promotion = PromotionStatus(
                eligible=eligibility.eligible,
                reasons=list(eligibility.reasons),
                severity=eligibility.severity.value if eligibility.severity else None,
            )

        return RegressionReportContext(
            title=f"Regression Report — {regression.feature}",
            generated_at=datetime.now(UTC),
            feature=regression.feature,
            baseline_run_id=regression.baseline_run_id,
            candidate_run_id=regression.candidate_run_id,
            baseline_prompt_version=regression.baseline_prompt_version,
            candidate_prompt_version=regression.candidate_prompt_version,
            baseline_dataset_version=regression.baseline_dataset_version,
            candidate_dataset_version=regression.candidate_dataset_version,
            prompt_changed=regression.prompt_changed,
            dataset_changed=regression.dataset_changed,
            severity=regression.severity.value,
            is_blocking=regression.is_blocking,
            warning_count=regression.warning_count,
            critical_count=regression.critical_count,
            regressed=list(regression.regressions),
            improved=improved,
            unchanged_count=unchanged,
            promotion=promotion,
        )

    # -- rendering --------------------------------------------------------------

    def render_evaluation(
        self, result: EvaluationResult, fmt: ReportFormat = ReportFormat.HTML
    ) -> RenderedReport:
        """Render an evaluation report in the requested format."""
        context = self.build_evaluation_context(result)
        content = self._render(_TEMPLATES[("evaluation", fmt)], context)
        logger.info(
            "Rendered evaluation %s report for run %s (%d chars)",
            fmt.value,
            result.run_id,
            len(content),
        )
        return RenderedReport(title=context.title, format=fmt, content=content)

    def render_regression(
        self,
        regression: RegressionResult,
        *,
        eligibility: PromotionEligibility | None = None,
        fmt: ReportFormat = ReportFormat.HTML,
    ) -> RenderedReport:
        """Render a regression report in the requested format."""
        context = self.build_regression_context(regression, eligibility=eligibility)
        content = self._render(_TEMPLATES[("regression", fmt)], context)
        logger.info(
            "Rendered regression %s report for %s -> %s (severity=%s, %d chars)",
            fmt.value,
            regression.baseline_run_id,
            regression.candidate_run_id,
            regression.severity.value,
            len(content),
        )
        return RenderedReport(title=context.title, format=fmt, content=content)

    def _render(self, template_name: str, context: object) -> str:
        return self._env.get_template(template_name).render(ctx=context)


def save_report(report: RenderedReport, path: Path) -> Path:
    """Write a rendered report to ``path`` (creating parent directories)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.content, encoding="utf-8")
    logger.info("Saved %s report to %s", report.format.value, path)
    return path
