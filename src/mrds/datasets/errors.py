"""Error hierarchy for the dataset-management subsystem."""

from __future__ import annotations


class DatasetError(Exception):
    """Base class for all dataset-management errors."""


class DatasetValidationError(DatasetError):
    """Raised when a dataset file is malformed or fails schema validation."""


class DatasetNotFoundError(DatasetError):
    """Raised when a requested feature/version is not in the registry."""
