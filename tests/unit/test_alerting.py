"""Tests for Slack alerting: message generation, webhook client, and failure handling."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from mrds.alerting import (
    Alert,
    AlertType,
    SlackClient,
    SlackNotifier,
    build_promotion_alert,
    build_regression_alert,
)
from mrds.alerting.models import AlertResult
from mrds.evaluation.models import (
    AggregateMetrics,
    EvaluationResult,
    LatencyStats,
    ScorerStats,
    TokenStats,
)
from mrds.regression.models import (
    MetricComparison,
    MetricKind,
    RegressionResult,
    Severity,
)

NOW = datetime(2026, 5, 29, tzinfo=UTC)


def _comparison(
    name: str, severity: Severity, *, base: float = 0.9, cand: float = 0.7
) -> MetricComparison:
    return MetricComparison(
        name=name,
        kind=MetricKind.QUALITY,
        baseline_value=base,
        candidate_value=cand,
        delta=cand - base,
        relative_delta=(cand - base) / base,
        severity=severity,
        regressed=severity is not Severity.PASS,
        reason=f"dropped {base - cand:.2f}",
    )


def _regression(severity: Severity) -> RegressionResult:
    if severity is Severity.PASS:
        regressions: list[MetricComparison] = []
    else:
        regressions = [_comparison("scorer.category_match.mean_score", severity)]
    return RegressionResult(
        feature="email_classifier",
        baseline_run_id="base-1",
        candidate_run_id="cand-1",
        baseline_prompt_version="v1",
        candidate_prompt_version="v2",
        baseline_dataset_version="v1",
        candidate_dataset_version="v1",
        prompt_changed=True,
        dataset_changed=False,
        severity=severity,
        comparisons=regressions,
        regressions=regressions,
        warning_count=1 if severity is Severity.WARNING else 0,
        critical_count=1 if severity is Severity.CRITICAL else 0,
    )


def _eval_result() -> EvaluationResult:
    return EvaluationResult(
        run_id="run-1",
        feature="email_classifier",
        prompt_version="v1",
        prompt_hash="ph",
        dataset_version="v1",
        dataset_hash="dh",
        model="gpt-4o-mini",
        start_time=NOW,
        end_time=NOW,
        duration_seconds=1.0,
        aggregate_metrics=AggregateMetrics(
            total_cases=1,
            passed=1,
            failed=0,
            errored=0,
            pass_rate=1.0,
            scorers={"s": ScorerStats(name="s", mean_score=1.0, pass_rate=1.0, passed=1, count=1)},
            segments={},
            segment_field=None,
            latency=LatencyStats(
                count=1, total_ms=1, mean_ms=1, min_ms=1, p50_ms=1, p95_ms=1, max_ms=1
            ),
            tokens=TokenStats(
                total_tokens=1, total_input_tokens=1, total_output_tokens=0, mean_tokens_per_case=1
            ),
        ),
        per_case_results=[],
    )


class FakeTransport:
    """Records the request and returns a configured status, or raises."""

    def __init__(self, status: int = 200, raise_exc: Exception | None = None) -> None:
        self.status = status
        self.raise_exc = raise_exc
        self.calls: list[tuple[str, bytes]] = []

    def __call__(self, url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        self.calls.append((url, body))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.status


# -- message generation ---------------------------------------------------------


def test_critical_regression_message() -> None:
    alert = build_regression_alert(_regression(Severity.CRITICAL), report_location="reports/x.html")
    assert alert is not None
    assert alert.type is AlertType.CRITICAL_REGRESSION
    blob = json.dumps(alert.payload())
    expected = ["CRITICAL", "email_classifier", "v2", "Regressions", "Critical", "reports/x.html"]
    for token in expected:
        assert token in blob, token


def test_warning_regression_message() -> None:
    alert = build_regression_alert(_regression(Severity.WARNING), report_location="reports/y.md")
    assert alert is not None
    assert alert.type is AlertType.WARNING_REGRESSION
    blob = json.dumps(alert.payload())
    assert "Warnings" in blob
    assert "scorer.category_match.mean_score" in blob  # regressed metric listed
    assert "reports/y.md" in blob


def test_no_regression_yields_no_alert() -> None:
    assert build_regression_alert(_regression(Severity.PASS)) is None


def test_promotion_message() -> None:
    alert = build_promotion_alert(_eval_result(), promoted_by="ci", note="green main")
    assert alert.type is AlertType.BASELINE_PROMOTION
    blob = json.dumps(alert.payload())
    for token in ["email_classifier", "run-1", "ci", "green main"]:
        assert token in blob, token


# -- payload validation ---------------------------------------------------------


def test_payload_is_json_serialisable_with_blocks() -> None:
    alert = build_regression_alert(_regression(Severity.CRITICAL))
    payload = alert.payload()
    assert "text" in payload and "blocks" in payload
    assert isinstance(payload["blocks"], list)
    json.dumps(payload)  # must not raise
    assert payload["blocks"][0]["type"] == "header"


# -- webhook client -------------------------------------------------------------


def test_client_delivers_on_2xx() -> None:
    transport = FakeTransport(status=200)
    result = SlackClient("https://hooks.example/x", transport=transport).send(
        build_promotion_alert(_eval_result(), promoted_by="ci")
    )
    assert result.delivered is True
    assert result.status_code == 200
    assert transport.calls and transport.calls[0][0] == "https://hooks.example/x"


def test_client_reports_non_2xx_without_raising() -> None:
    result = SlackClient("https://hooks.example/x", transport=FakeTransport(status=500)).send(
        build_promotion_alert(_eval_result(), promoted_by="ci")
    )
    assert result.delivered is False
    assert result.status_code == 500


def test_client_swallows_transport_exception() -> None:
    transport = FakeTransport(raise_exc=ConnectionError("boom"))
    result = SlackClient("https://hooks.example/x", transport=transport).send(
        build_promotion_alert(_eval_result(), promoted_by="ci")
    )
    assert result.delivered is False
    assert "boom" in (result.error or "")


# -- notifier / failure handling ------------------------------------------------


def test_notifier_delivers_regression() -> None:
    transport = FakeTransport(status=200)
    notifier = SlackNotifier(client=SlackClient("https://hooks.example/x", transport=transport))
    result = notifier.notify_regression(_regression(Severity.CRITICAL), report_location="r.html")
    assert result.delivered is True
    assert result.alert_type is AlertType.CRITICAL_REGRESSION


def test_notifier_without_webhook_skips_safely() -> None:
    notifier = SlackNotifier(webhook_url=None)
    assert notifier.enabled is False
    result = notifier.notify_promotion(_eval_result(), promoted_by="ci")
    assert result.skipped is True
    assert result.delivered is False


def test_notifier_skips_when_no_regression() -> None:
    client = SlackClient("https://hooks.example/x", transport=FakeTransport())
    notifier = SlackNotifier(client=client)
    result = notifier.notify_regression(_regression(Severity.PASS))
    assert result.skipped is True
    assert result.delivered is False


def test_notifier_never_raises_on_send_failure() -> None:
    transport = FakeTransport(raise_exc=TimeoutError("slow"))
    notifier = SlackNotifier(client=SlackClient("https://hooks.example/x", transport=transport))
    result = notifier.notify_regression(_regression(Severity.WARNING))
    assert result.delivered is False
    assert result.error is not None


def test_notifier_resolves_webhook_from_settings(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example/from-settings")
    notifier = SlackNotifier()
    assert notifier.enabled is True


def test_notifier_swallows_build_errors() -> None:
    client = SlackClient("https://hooks.example/x", transport=FakeTransport())
    notifier = SlackNotifier(client=client)
    # Force a build error by passing a regression whose attribute access blows up.
    result = notifier._safe(lambda: (_ for _ in ()).throw(ValueError("bad build")))
    assert result.delivered is False
    assert "bad build" in (result.error or "")
    assert isinstance(result, AlertResult)


def test_alert_model_payload_shape() -> None:
    alert = Alert(type=AlertType.BASELINE_PROMOTION, text="hi", blocks=[{"type": "section"}])
    assert alert.payload() == {"text": "hi", "blocks": [{"type": "section"}]}
