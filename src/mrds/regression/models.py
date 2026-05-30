"""Models for regression results and the baseline-promotion workflow.

Everything here is feature/dataset/prompt-agnostic: metrics are referenced by
dynamically-discovered string names, never by hardcoded metric identities.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from mrds.evaluation.models import EvaluationResult


class Severity(StrEnum):
    """Outcome severity for a metric comparison or an overall run."""

    PASS = "pass"
    WARNING = "warning"
    CRITICAL = "critical"


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.PASS: 0,
    Severity.WARNING: 1,
    Severity.CRITICAL: 2,
}


def worst_severity(severities: Iterable[Severity]) -> Severity:
    """Return the highest (worst) severity, defaulting to PASS when empty."""
    return max(severities, key=lambda s: _SEVERITY_RANK[s], default=Severity.PASS)


class MetricKind(StrEnum):
    """How a metric should be interpreted when comparing runs."""

    QUALITY = "quality"  # higher is better; a drop is a regression
    LATENCY = "latency"  # lower is better; an increase is a regression
    TOKENS = "tokens"  # lower is better; an increase is a regression
    ERRORS = "errors"  # lower is better; an increase is a regression


class MetricComparison(BaseModel):
    """The comparison of a single metric between baseline and candidate."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: MetricKind
    baseline_value: float
    candidate_value: float
    delta: float  # candidate - baseline
    relative_delta: float | None  # delta / baseline, or None if baseline == 0
    severity: Severity
    regressed: bool
    reason: str


class RegressionResult(BaseModel):
    """The full outcome of comparing a candidate run against a baseline run."""

    model_config = ConfigDict(frozen=True)

    feature: str
    baseline_run_id: str
    candidate_run_id: str
    baseline_prompt_version: str
    candidate_prompt_version: str
    baseline_dataset_version: str
    candidate_dataset_version: str
    prompt_changed: bool
    dataset_changed: bool
    severity: Severity
    comparisons: list[MetricComparison] = Field(default_factory=list)
    regressions: list[MetricComparison] = Field(default_factory=list)
    warning_count: int = 0
    critical_count: int = 0

    @property
    def has_regression(self) -> bool:
        """True if any metric regressed (WARNING or CRITICAL)."""
        return self.severity != Severity.PASS

    @property
    def is_blocking(self) -> bool:
        """True if this regression should block a deployment (CRITICAL)."""
        return self.severity == Severity.CRITICAL


class Baseline(BaseModel):
    """A promoted, known-good run plus its promotion metadata."""

    model_config = ConfigDict(frozen=True)

    feature: str
    result: EvaluationResult
    promoted_at: datetime
    promoted_by: str
    note: str = ""

    @property
    def run_id(self) -> str:
        return self.result.run_id

    @property
    def prompt_version(self) -> str:
        return self.result.prompt_version

    @property
    def dataset_version(self) -> str:
        return self.result.dataset_version


class BaselineCandidate(BaseModel):
    """A run proposed for promotion to baseline."""

    model_config = ConfigDict(frozen=True)

    result: EvaluationResult

    @property
    def feature(self) -> str:
        return self.result.feature

    @property
    def run_id(self) -> str:
        return self.result.run_id


class PromotionEligibility(BaseModel):
    """The decision of whether a candidate may be promoted to baseline."""

    model_config = ConfigDict(frozen=True)

    eligible: bool
    reasons: list[str] = Field(default_factory=list)
    severity: Severity | None = None
    regression: RegressionResult | None = None
