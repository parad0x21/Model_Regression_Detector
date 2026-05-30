"""Identifier generation for runs and log correlation.

Each evaluation run gets a unique ``run_id`` that is used as a correlation ID
across logs, reports, and (later) the SQLite system of record.
"""

from __future__ import annotations

import uuid


def new_run_id() -> str:
    """Return a new, unique run identifier (hex UUID4)."""
    return uuid.uuid4().hex


# Alias: a run id doubles as a log correlation id.
new_correlation_id = new_run_id
