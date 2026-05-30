"""The baseline-promotion workflow.

Candidate Run -> Compare Against Baseline -> Pass/Fail Decision -> Optional Promotion.

A candidate is eligible unless it has a CRITICAL regression against the current
baseline (and, optionally, unless warnings are disallowed). Baselines are never
silently overwritten by a worse run — promotion is explicit.
"""

from __future__ import annotations

from datetime import UTC, datetime

from mrds.observability.logging import get_logger
from mrds.regression.detector import RegressionDetector
from mrds.regression.errors import PromotionNotEligibleError
from mrds.regression.models import (
    Baseline,
    BaselineCandidate,
    PromotionEligibility,
    Severity,
)

logger = get_logger(__name__)


class BaselinePromoter:
    """Decides eligibility and performs baseline promotion."""

    def __init__(
        self,
        detector: RegressionDetector | None = None,
        *,
        allow_warnings: bool = True,
    ) -> None:
        self._detector = detector or RegressionDetector()
        self._allow_warnings = allow_warnings

    def check(self, candidate: BaselineCandidate, current: Baseline | None) -> PromotionEligibility:
        """Return whether ``candidate`` may be promoted given the ``current`` baseline."""
        if current is None:
            return PromotionEligibility(
                eligible=True, reasons=["No existing baseline; first promotion is always eligible."]
            )

        if current.feature != candidate.feature:
            return PromotionEligibility(
                eligible=False,
                reasons=[
                    f"Feature mismatch: baseline '{current.feature}' vs "
                    f"candidate '{candidate.feature}'."
                ],
            )

        regression = self._detector.compare(current.result, candidate.result)

        if regression.is_blocking:
            return PromotionEligibility(
                eligible=False,
                reasons=["Candidate has a CRITICAL regression against the current baseline."],
                severity=regression.severity,
                regression=regression,
            )

        if regression.severity == Severity.WARNING and not self._allow_warnings:
            return PromotionEligibility(
                eligible=False,
                reasons=["Candidate has a WARNING regression and warnings are disallowed."],
                severity=regression.severity,
                regression=regression,
            )

        return PromotionEligibility(
            eligible=True,
            reasons=["No blocking regression against the current baseline."],
            severity=regression.severity,
            regression=regression,
        )

    def promote(
        self,
        candidate: BaselineCandidate,
        *,
        current: Baseline | None = None,
        promoted_by: str = "manual",
        note: str = "",
        force: bool = False,
    ) -> Baseline:
        """Promote ``candidate`` to a new baseline.

        Raises:
            PromotionNotEligibleError: If the candidate is ineligible and ``force``
                is not set.
        """
        eligibility = self.check(candidate, current)
        if not eligibility.eligible and not force:
            raise PromotionNotEligibleError("; ".join(eligibility.reasons))

        baseline = Baseline(
            feature=candidate.feature,
            result=candidate.result,
            promoted_at=datetime.now(UTC),
            promoted_by=promoted_by,
            note=note,
        )
        logger.info(
            "Promoted baseline for %s: run=%s by=%s force=%s",
            baseline.feature,
            baseline.run_id,
            promoted_by,
            force,
        )
        return baseline
