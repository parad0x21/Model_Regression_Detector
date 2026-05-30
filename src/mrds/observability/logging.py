"""Structured logging foundation.

Every log record carries a ``run_id`` correlation field so that local runs, CI
runs, and (later) database records can be cross-referenced. The active run id is
stored in a :class:`contextvars.ContextVar` and injected via a logging filter,
so callers do not have to thread it through every log call.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar, Token

_DEFAULT_RUN_ID = "-"
_run_id_var: ContextVar[str] = ContextVar("mrds_run_id", default=_DEFAULT_RUN_ID)

_TEXT_FORMAT = "%(asctime)s %(levelname)s [run=%(run_id)s] %(name)s: %(message)s"
_JSON_FORMAT = (
    '{"ts":"%(asctime)s","level":"%(levelname)s","run_id":"%(run_id)s",'
    '"logger":"%(name)s","msg":"%(message)s"}'
)


class _RunIdFilter(logging.Filter):
    """Inject the current ``run_id`` correlation value onto every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = _run_id_var.get()
        return True


def configure_logging(level: str = "INFO", *, json_logs: bool = False) -> None:
    """Configure the root logger for the process.

    Args:
        level: Logging level name (e.g. ``"INFO"``, ``"DEBUG"``).
        json_logs: Emit JSON-shaped lines instead of human-readable text.
    """
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_JSON_FORMAT if json_logs else _TEXT_FORMAT))
    handler.addFilter(_RunIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (thin wrapper over :func:`logging.getLogger`)."""
    return logging.getLogger(name)


def set_run_id(run_id: str) -> Token[str]:
    """Set the active run correlation id; returns a token for :func:`reset_run_id`."""
    return _run_id_var.set(run_id)


def reset_run_id(token: Token[str]) -> None:
    """Reset the active run correlation id using a token from :func:`set_run_id`."""
    _run_id_var.reset(token)


class bind_run_id:  # noqa: N801 - context-manager helper named like a verb
    """Context manager that binds a ``run_id`` for the duration of a block."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._token: Token[str] | None = None

    def __enter__(self) -> str:
        self._token = set_run_id(self._run_id)
        return self._run_id

    def __exit__(self, *exc: object) -> None:
        if self._token is not None:
            reset_run_id(self._token)
