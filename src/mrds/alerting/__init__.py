"""Slack alerting — a best-effort *consumer* of evaluation/regression results.

Alerting never affects pass/fail: delivery is best-effort and every public call
returns an :class:`AlertResult` rather than raising. The webhook URL is resolved
from settings (``SLACK_WEBHOOK_URL``).
"""

from mrds.alerting.messages import build_promotion_alert, build_regression_alert
from mrds.alerting.models import Alert, AlertResult, AlertType
from mrds.alerting.notifier import SlackNotifier
from mrds.alerting.slack import SlackClient

__all__ = [
    "Alert",
    "AlertResult",
    "AlertType",
    "SlackClient",
    "SlackNotifier",
    "build_promotion_alert",
    "build_regression_alert",
]
