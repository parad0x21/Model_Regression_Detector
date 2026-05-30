"""Slack incoming-webhook client.

Delivery is **best-effort**: :meth:`SlackClient.send` never raises — any transport
error is logged and returned as a non-delivered :class:`AlertResult`, so alerting
can never affect evaluation pass/fail. The HTTP transport is injectable so tests
need no network.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.request import Request, urlopen

from mrds.alerting.models import Alert, AlertResult
from mrds.observability.logging import get_logger

logger = get_logger(__name__)

# (url, body, headers, timeout) -> HTTP status code
Transport = Callable[[str, bytes, dict[str, str], float], int]


def _urllib_transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed webhook URL
        return int(response.status)


class SlackClient:
    """Posts :class:`Alert`s to a Slack incoming webhook (best-effort)."""

    def __init__(
        self,
        webhook_url: str,
        *,
        timeout: float = 5.0,
        transport: Transport = _urllib_transport,
    ) -> None:
        self._url = webhook_url
        self._timeout = timeout
        self._transport = transport

    def send(self, alert: Alert) -> AlertResult:
        """Attempt delivery; return an :class:`AlertResult`, never raising."""
        body = json.dumps(alert.payload()).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        try:
            status = self._transport(self._url, body, headers, self._timeout)
        except Exception as exc:  # noqa: BLE001 - best-effort: failures must not propagate
            logger.error("Slack delivery failed for %s: %s", alert.type.value, exc)
            return AlertResult(alert_type=alert.type, delivered=False, error=str(exc))

        delivered = 200 <= status < 300
        if not delivered:
            logger.warning("Slack returned status %d for %s", status, alert.type.value)
        else:
            logger.info("Delivered %s alert to Slack", alert.type.value)
        return AlertResult(alert_type=alert.type, delivered=delivered, status_code=status)
