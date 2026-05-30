"""Reporting: human-readable HTML and Markdown evaluation/regression reports.

Clean separation: :class:`ReportBuilder` holds all report logic and renders
feature-agnostic Jinja2 templates that only read context models.
"""

from mrds.reporting.builder import ReportBuilder, save_report
from mrds.reporting.models import (
    EvaluationReportContext,
    PromotionStatus,
    RegressionReportContext,
    RenderedReport,
    ReportFormat,
)

__all__ = [
    "EvaluationReportContext",
    "PromotionStatus",
    "RegressionReportContext",
    "RenderedReport",
    "ReportBuilder",
    "ReportFormat",
    "save_report",
]
