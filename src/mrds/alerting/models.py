"""Alert models — provider-neutral alert payloads and delivery results.

An :class:`Alert` carries a Slack-ready payload (fallback text + Block Kit blocks);
an :class:`AlertResult` records the outcome of attempting to deliver one. Nothing
here performs I/O.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AlertType(StrEnum):
    """The kinds of alerts the platform emits."""

    CRITICAL_REGRESSION = "critical_regression"
    WARNING_REGRESSION = "warning_regression"
    BASELINE_PROMOTION = "baseline_promotion"


class Alert(BaseModel):
    """A ready-to-send alert: fallback text plus Block Kit blocks."""

    model_config = ConfigDict(frozen=True)

    type: AlertType
    text: str  # plain-text fallback (notifications, screen readers)
    blocks: list[dict[str, Any]] = Field(default_factory=list)

    def payload(self) -> dict[str, Any]:
        """Return the JSON body Slack's incoming-webhook API expects."""
        return {"text": self.text, "blocks": self.blocks}


class AlertResult(BaseModel):
    """The outcome of attempting to deliver an alert (never an exception)."""

    model_config = ConfigDict(frozen=True)

    alert_type: AlertType | None
    delivered: bool
    skipped: bool = False
    status_code: int | None = None
    error: str | None = None
