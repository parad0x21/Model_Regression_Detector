"""High-level, settings-aware notifier.

:class:`SlackNotifier` ties the message builders to the webhook client and resolves
the webhook URL from settings. Every ``notify_*`` method is total: it returns an
:class:`AlertResult` and never raises, so a missing webhook, a build error, or a
delivery failure can never break an evaluation run.
"""

from __future__ import annotations

from collections.abc import Callable

from mrds.alerting.messages import build_promotion_alert, build_regression_alert
from mrds.alerting.models import Alert, AlertResult
from mrds.alerting.slack import SlackClient
from mrds.config.settings import Settings, get_settings
from mrds.evaluation.models import EvaluationResult
from mrds.observability.logging import get_logger
from mrds.regression.models import PromotionEligibility, RegressionResult

logger = get_logger(__name__)


class SlackNotifier:
    """Builds and delivers alerts, resolving the webhook from settings."""

    def __init__(
        self,
        *,
        webhook_url: str | None = None,
        client: SlackClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        if client is not None:
            self._client: SlackClient | None = client
        else:
            url = webhook_url or (settings or get_settings()).slack_webhook_url
            self._client = SlackClient(url) if url else None

    @property
    def enabled(self) -> bool:
        """True if a webhook is configured and alerts will be attempted."""
        return self._client is not None

    def notify_regression(
        self, regression: RegressionResult, *, report_location: str | None = None
    ) -> AlertResult:
        """Send a regression alert (skipped silently if there is no regression)."""
        return self._safe(
            lambda: build_regression_alert(regression, report_location=report_location)
        )

    def notify_promotion(
        self,
        result: EvaluationResult,
        *,
        promoted_by: str,
        note: str = "",
        eligibility: PromotionEligibility | None = None,
    ) -> AlertResult:
        """Send a baseline-promotion alert."""
        return self._safe(
            lambda: build_promotion_alert(
                result, promoted_by=promoted_by, note=note, eligibility=eligibility
            )
        )

    def _safe(self, build: Callable[[], Alert | None]) -> AlertResult:
        try:
            alert = build()
        except Exception as exc:  # noqa: BLE001 - alerting must never break a run
            logger.error("Failed to build alert: %s", exc)
            return AlertResult(alert_type=None, delivered=False, error=str(exc))

        if alert is None:
            return AlertResult(alert_type=None, delivered=False, skipped=True)
        if self._client is None:
            logger.info("No Slack webhook configured; skipping %s alert", alert.type.value)
            return AlertResult(alert_type=alert.type, delivered=False, skipped=True)

        try:
            return self._client.send(alert)
        except Exception as exc:  # noqa: BLE001 - defensive; SlackClient already swallows
            logger.error("Failed to send alert: %s", exc)
            return AlertResult(alert_type=alert.type, delivered=False, error=str(exc))
