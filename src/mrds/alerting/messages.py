"""Block Kit message builders.

Pure functions that turn domain objects (:class:`RegressionResult`,
:class:`EvaluationResult`, :class:`PromotionEligibility`) into :class:`Alert`s.
Feature-agnostic: metric names come straight from the regression result.
"""

from __future__ import annotations

from typing import Any

from mrds.alerting.models import Alert, AlertType
from mrds.evaluation.models import EvaluationResult
from mrds.regression.models import PromotionEligibility, RegressionResult, Severity

_MAX_METRIC_LINES = 10


def _header(text: str) -> dict[str, Any]:
    return {"type": "header", "text": {"type": "plain_text", "text": text[:150]}}


def _section_fields(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "type": "section",
        "fields": [{"type": "mrkdwn", "text": f"*{key}:*\n{value}"} for key, value in pairs[:10]],
    }


def _section_text(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _context(text: str) -> dict[str, Any]:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def _metric_lines(regression: RegressionResult) -> str:
    lines = [
        f"• `{m.name}`: {m.reason} ({m.severity.value})"
        for m in regression.regressions[:_MAX_METRIC_LINES]
    ]
    extra = len(regression.regressions) - _MAX_METRIC_LINES
    if extra > 0:
        lines.append(f"• …and {extra} more")
    return "\n".join(lines)


def build_regression_alert(
    regression: RegressionResult, *, report_location: str | None = None
) -> Alert | None:
    """Build a regression alert, or ``None`` if there is no regression to report."""
    if regression.severity is Severity.PASS:
        return None

    critical = regression.severity is Severity.CRITICAL
    if critical:
        alert_type = AlertType.CRITICAL_REGRESSION
        title = f"🔴 Critical regression — {regression.feature}"
        fields = [
            ("Severity", regression.severity.value.upper()),
            ("Feature", regression.feature),
            ("Prompt", regression.candidate_prompt_version),
            ("Dataset", regression.candidate_dataset_version),
            ("Regressions", str(len(regression.regressions))),
            ("Critical", str(regression.critical_count)),
        ]
    else:
        alert_type = AlertType.WARNING_REGRESSION
        title = f"🟡 Warning regression — {regression.feature}"
        fields = [
            ("Feature", regression.feature),
            ("Warnings", str(regression.warning_count)),
            ("Regressions", str(len(regression.regressions))),
        ]

    blocks: list[dict[str, Any]] = [_header(title), _section_fields(fields)]
    if regression.regressions:
        blocks.append(_section_text(f"*Regressed metrics:*\n{_metric_lines(regression)}"))
    blocks.append(
        _context(
            f"Candidate `{regression.candidate_run_id}` vs baseline `{regression.baseline_run_id}`"
        )
    )
    if report_location:
        blocks.append(_context(f"Report: {report_location}"))

    return Alert(type=alert_type, text=title, blocks=blocks)


def build_promotion_alert(
    result: EvaluationResult,
    *,
    promoted_by: str,
    note: str = "",
    eligibility: PromotionEligibility | None = None,
) -> Alert:
    """Build a baseline-promotion alert."""
    title = f"🟢 Baseline promoted — {result.feature}"
    fields = [
        ("Feature", result.feature),
        ("Run", result.run_id),
        ("Promoted by", promoted_by),
    ]
    blocks: list[dict[str, Any]] = [_header(title), _section_fields(fields)]
    if note:
        blocks.append(_section_text(f"*Note:* {note}"))
    if eligibility is not None and eligibility.severity is not None:
        blocks.append(_context(f"Severity vs previous baseline: {eligibility.severity.value}"))
    return Alert(type=AlertType.BASELINE_PROMOTION, text=title, blocks=blocks)
