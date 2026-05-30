"""Error hierarchy for the regression subsystem."""

from __future__ import annotations


class RegressionError(Exception):
    """Base class for regression-detection and baseline errors."""


class PromotionNotEligibleError(RegressionError):
    """Raised when a baseline promotion is attempted but is not eligible."""
