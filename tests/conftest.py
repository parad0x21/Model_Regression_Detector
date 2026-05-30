"""Shared pytest fixtures for the MRDS test suite."""

from __future__ import annotations

import pytest


@pytest.fixture
def clear_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove secret env vars so default-value tests are hermetic.

    CI environments may export ``OPENAI_API_KEY`` / ``SLACK_WEBHOOK_URL``; tests
    asserting default behaviour should not depend on the host environment.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
