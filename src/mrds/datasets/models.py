"""Pydantic v2 models for versioned golden datasets.

The dataset models are *generic* over a feature's input and output models, so the
same models validate datasets for any feature (``email_classifier`` today,
``rag_qa``/``chatbot`` later) with no changes. Concrete validation happens by
parametrising :class:`DatasetDefinition` with the feature's models, e.g.
``DatasetDefinition[EmailClassificationInput, EmailClassificationOutput]``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

VERSION_PATTERN = re.compile(r"^v\d+$")

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Difficulty(StrEnum):
    """Human-assessed difficulty of a labeled case."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class DatasetCase(BaseModel, Generic[InputT, OutputT]):
    """One human-labeled evaluation case."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Unique case identifier within the dataset.")
    input: InputT = Field(description="Feature input (validated against the feature's model).")
    expected_output: OutputT = Field(description="Human-labeled expected output.")
    expected_difficulty: Difficulty = Field(description="Human-assessed difficulty.")
    notes: str = Field(default="", description="Optional rationale / edge-case annotation.")

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value


class DatasetDefinition(BaseModel, Generic[InputT, OutputT]):
    """A single versioned golden dataset, as parsed from a JSON file.

    Human identity is ``(feature, version)``; change-detection identity is the
    content hash (see :func:`mrds.datasets.loader.compute_content_hash`), which
    excludes the provenance-only ``created_at`` field.
    """

    model_config = ConfigDict(extra="forbid")

    version: str = Field(description="Version label, e.g. 'v1'.")
    created_at: date = Field(description="Authoring date (provenance only).")
    description: str = Field(min_length=1, description="Human summary of this dataset version.")
    cases: list[DatasetCase[InputT, OutputT]] = Field(
        min_length=1, description="The labeled evaluation cases."
    )

    @field_validator("version")
    @classmethod
    def _valid_version(cls, value: str) -> str:
        if not VERSION_PATTERN.match(value):
            raise ValueError("version must match 'v<number>' (e.g. 'v1', 'v2')")
        return value

    @field_validator("description")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("cases")
    @classmethod
    def _unique_ids(cls, cases: list[DatasetCase[Any, Any]]) -> list[DatasetCase[Any, Any]]:
        ids = [case.id for case in cases]
        if len(set(ids)) != len(ids):
            raise ValueError("case ids must be unique within a dataset")
        return cases

    @property
    def version_number(self) -> int:
        """Numeric component of the version label (``v3`` -> ``3``)."""
        return int(self.version[1:])

    @property
    def case_count(self) -> int:
        """Number of cases in the dataset."""
        return len(self.cases)


@dataclass(frozen=True)
class LoadedDataset:
    """A validated dataset plus its resolved identity, hash, and provenance.

    Implemented as a frozen dataclass (not a Pydantic model) so the generic
    ``definition`` is stored as-is without re-validation.
    """

    feature: str
    definition: DatasetDefinition[Any, Any]
    content_hash: str
    source_path: Path

    @property
    def version(self) -> str:
        """Convenience accessor for the dataset version label."""
        return self.definition.version

    @property
    def case_count(self) -> int:
        """Number of cases in the dataset."""
        return self.definition.case_count

    @property
    def identity(self) -> str:
        """Human-readable identity, e.g. ``email_classifier:v1``."""
        return f"{self.feature}:{self.version}"
