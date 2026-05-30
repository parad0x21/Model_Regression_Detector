"""Read-only data access for the dashboard.

This module has **no Streamlit dependency** — it is the testable seam between the
persisted data and the presentation pages. It reuses :class:`EvaluationStore` and
its repositories; the only derived computation is parsing each run's stored
metrics snapshot into chartable :class:`TrendPoint`s. Nothing here writes.
"""

from __future__ import annotations

from dataclasses import dataclass

from mrds.db import EvaluationStore
from mrds.db.records import BaselineRecord, RegressionRecord, RunRecord
from mrds.evaluation.models import AggregateMetrics, EvaluationResult
from mrds.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class TrendPoint:
    """One point in a feature's metric time-series (derived from a run)."""

    run_uuid: str
    started_at: str
    pass_rate: float
    errored: int
    mean_latency_ms: float
    p95_latency_ms: float
    total_tokens: int
    scorer_means: dict[str, float]


class DashboardData:
    """Read-only queries backing the dashboard pages."""

    def __init__(self, store: EvaluationStore) -> None:
        self._store = store

    def features(self) -> list[str]:
        """Feature names that have at least one recorded run."""
        return self._store.runs.features()

    def runs(self, feature: str, *, limit: int = 100) -> list[RunRecord]:
        """Most-recent-first runs for a feature."""
        return self._store.runs.list_for_feature(feature, limit=limit)

    def run_detail(self, run_uuid: str) -> EvaluationResult | None:
        """Full reconstructed run (metadata, metrics, per-case results)."""
        return self._store.get_evaluation_result(run_uuid)

    def regressions_for_run(self, run_uuid: str) -> list[RegressionRecord]:
        """Persisted regressions where ``run_uuid`` is the candidate."""
        run = self._store.runs.get_by_uuid(run_uuid)
        if run is None:
            return []
        return self._store.regressions.list_for_run(run.id)

    def active_baseline(self, feature: str) -> BaselineRecord | None:
        """The currently active baseline for a feature, if any."""
        return self._store.baselines.get_active(feature)

    def baseline_history(self, feature: str) -> list[BaselineRecord]:
        """All baseline promotions for a feature, most recent first."""
        return self._store.baselines.history(feature)

    def run_uuid_for(self, run_db_id: int) -> str | None:
        """Resolve a run's UUID from its database id (for baseline display)."""
        run = self._store.runs.get_by_id(run_db_id)
        return run.run_uuid if run else None

    def trend(self, feature: str, *, limit: int = 100) -> list[TrendPoint]:
        """Chronological metric series for a feature, parsed from run snapshots."""
        points: list[TrendPoint] = []
        for record in reversed(self.runs(feature, limit=limit)):  # oldest -> newest
            metrics = AggregateMetrics.model_validate_json(record.metrics_json)
            points.append(
                TrendPoint(
                    run_uuid=record.run_uuid,
                    started_at=record.started_at,
                    pass_rate=metrics.pass_rate,
                    errored=metrics.errored,
                    mean_latency_ms=metrics.latency.mean_ms,
                    p95_latency_ms=metrics.latency.p95_ms,
                    total_tokens=metrics.tokens.total_tokens,
                    scorer_means={name: s.mean_score for name, s in metrics.scorers.items()},
                )
            )
        return points
