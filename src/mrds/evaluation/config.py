"""Configuration for a single evaluation run.

Feature-agnostic: ``segment_field`` names an arbitrary field on the expected
output to break metrics down by (e.g. ``"category"`` yields per-category metrics
for the email classifier) without the engine knowing anything about that field.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvaluationConfig(BaseModel):
    """Inputs that fully determine an evaluation run."""

    model_config = ConfigDict(extra="forbid")

    feature: str = Field(min_length=1, description="Registered feature name to evaluate.")
    prompt_version: str | None = Field(
        default=None, description="Prompt version label; None resolves to the latest."
    )
    dataset_version: str | None = Field(
        default=None, description="Dataset version label; None resolves to the latest."
    )
    segment_field: str | None = Field(
        default=None,
        description="Expected-output field to break metrics down by (e.g. 'category').",
    )
    max_cases: int | None = Field(
        default=None, ge=1, description="Optional cap on cases evaluated (for smoke runs)."
    )
