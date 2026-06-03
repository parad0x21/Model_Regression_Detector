"""Read-only data access for the dashboard.

This module has **no Streamlit dependency** — it is the testable seam between the
persisted data and the presentation pages. It reuses :class:`EvaluationStore` and
its repositories; the only derived computation is parsing each run's stored
metrics snapshot into chartable :class:`TrendPoint`s. Nothing here writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mrds.db import EvaluationStore
from mrds.db.records import BaselineRecord, RegressionRecord, RunRecord
from mrds.evaluation.models import AggregateMetrics, CaseResult, EvaluationResult
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


@dataclass(frozen=True)
class RunLabel:
    """A human-readable identity for a run, paired with its internal ``run_uuid``.

    The label is **display-only**; ``run_uuid`` remains the value behind every widget
    so run selection is unaffected (see ``build_run_label``).
    """

    run_uuid: str
    sequence: int
    label: str  # full, e.g. "Email Classifier #12 · gpt-4o-mini · Dataset v1 · Jun 2, 2026"
    short_label: str  # compact, for chart axes, e.g. "#12 · Jun 2"


def _humanize_feature(feature: str) -> str:
    """Turn a feature slug into a title-cased display name (e.g. ``Email Classifier``)."""
    return feature.replace("_", " ").title()


def _parse_started_at(started_at: str) -> datetime | None:
    try:
        return datetime.fromisoformat(started_at)
    except ValueError:
        return None


def build_run_label(
    *,
    run_uuid: str,
    feature: str,
    sequence: int,
    model: str,
    dataset_version: str,
    started_at: str,
) -> RunLabel:
    """Build a :class:`RunLabel` from a run's display fields (pure; no I/O).

    Components that are missing (no model / dataset version / unparseable date) are
    simply omitted, so the label degrades gracefully. ``run_uuid`` is never altered.
    """
    feature_name = _humanize_feature(feature)
    dt = _parse_started_at(started_at)
    full_date = f"{dt:%b} {dt.day}, {dt.year}" if dt else ""
    short_date = f"{dt:%b} {dt.day}" if dt else ""

    parts = [f"{feature_name} #{sequence}"]
    if model:
        parts.append(model)
    if dataset_version:
        parts.append(f"Dataset {dataset_version}")
    if full_date:
        parts.append(full_date)

    short = f"#{sequence}" + (f" · {short_date}" if short_date else "")
    return RunLabel(
        run_uuid=run_uuid,
        sequence=sequence,
        label=" · ".join(parts),
        short_label=short,
    )


@dataclass(frozen=True)
class ScorerExplanation:
    """One scorer's verdict on a case, with its human-readable reason."""

    name: str
    passed: bool
    score: float
    detail: str


@dataclass(frozen=True)
class CaseExplanation:
    """A presentation-ready view of one case: *why* it passed, failed, or errored.

    Pure and feature-agnostic — derived entirely from a stored :class:`CaseResult`
    (no I/O). This is the shared shape behind the per-case detail component, reused by
    the failures view, the test-log explorer, and root-cause drilldowns.
    """

    case_id: str
    difficulty: str
    passed: bool
    errored: bool
    input: dict[str, object]
    input_text: str  # best-effort primary text of the input (empty if not obvious)
    expected: dict[str, object]
    actual: dict[str, object] | None
    error: str | None
    scorers: tuple[ScorerExplanation, ...]
    failed_scorers: tuple[str, ...]
    summary: str  # one-line plain-English verdict


def _primary_input_text(input_data: dict[str, object]) -> str:
    """Return the single string field of an input dict, if there is exactly one."""
    str_values = [value for value in input_data.values() if isinstance(value, str)]
    return str_values[0] if len(str_values) == 1 else ""


def explain_case(case: CaseResult) -> CaseExplanation:
    """Derive a plain-English explanation of a single case's outcome (pure).

    Surfaces what was already stored but never shown: the model's ``actual`` output
    against the ``expected`` output, and each scorer's ``detail`` reason.
    """
    errored = case.error is not None
    scorers = tuple(
        ScorerExplanation(name=s.name, passed=s.passed, score=s.score, detail=s.detail)
        for s in case.scores
    )
    failed_scorers = tuple(s.name for s in scorers if not s.passed)

    if errored:
        summary = f"Errored — {case.error}"
    elif case.passed:
        summary = "All checks passed."
    else:
        failing = [s for s in scorers if not s.passed]
        summary = (
            "; ".join(f"{s.name}: {s.detail}" for s in failing if s.detail)
            or "; ".join(s.name for s in failing)
            or "Marked failed."
        )

    return CaseExplanation(
        case_id=case.case_id,
        difficulty=case.expected_difficulty.value,
        passed=case.passed,
        errored=errored,
        input=case.input,
        input_text=_primary_input_text(case.input),
        expected=case.expected_output,
        actual=case.actual_output,
        error=case.error,
        scorers=scorers,
        failed_scorers=failed_scorers,
        summary=summary,
    )


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

    def run_labels(self, feature: str, *, limit: int = 100) -> list[RunLabel]:
        """Human-readable labels for a feature's runs, most-recent-first.

        Built from the lightweight run rows plus a per-distinct-id dataset-version
        lookup (cached) — never a full per-run reconstruction. The per-feature
        sequence number is assigned within the returned window (oldest = #1).
        """
        runs = self.runs(feature, limit=limit)
        total = len(runs)
        version_cache: dict[int, str] = {}
        labels: list[RunLabel] = []
        for index, record in enumerate(runs):
            labels.append(
                build_run_label(
                    run_uuid=record.run_uuid,
                    feature=record.feature_name,
                    sequence=total - index,  # most-recent-first list -> newest gets the highest #
                    model=record.model,
                    dataset_version=self._dataset_version(record.dataset_version_id, version_cache),
                    started_at=record.started_at,
                )
            )
        return labels

    def run_label_map(self, feature: str, *, limit: int = 100) -> dict[str, RunLabel]:
        """``run_uuid -> RunLabel`` for a feature's runs (for lookup by uuid)."""
        return {label.run_uuid: label for label in self.run_labels(feature, limit=limit)}

    def _dataset_version(self, dataset_version_id: int | None, cache: dict[int, str]) -> str:
        """Resolve a dataset version string by id, caching distinct lookups."""
        if dataset_version_id is None:
            return ""
        if dataset_version_id not in cache:
            record = self._store.dataset_versions.get_by_id(dataset_version_id)
            cache[dataset_version_id] = record.version if record else ""
        return cache[dataset_version_id]

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
