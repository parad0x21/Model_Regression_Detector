"""Validation of raw dataset data against a feature's input/output models.

This is the single place that turns an untrusted mapping (parsed from JSON) into
a validated :class:`DatasetDefinition`, parametrising the generic model with the
feature's concrete input/output models. Keeping it separate from the loader
isolates *schema* concerns from *file I/O* concerns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from mrds.datasets.errors import DatasetValidationError
from mrds.datasets.models import DatasetDefinition


def validate_dataset_data(
    data: Any,
    *,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
    source: Path | None = None,
) -> DatasetDefinition[Any, Any]:
    """Validate parsed dataset data into a typed :class:`DatasetDefinition`.

    Args:
        data: The object parsed from a dataset file (expected: a mapping).
        input_model: The feature's input model; each case ``input`` is validated against it.
        output_model: The feature's output model; each ``expected_output`` is validated against it.
        source: Optional source path, for clearer error messages.

    Raises:
        DatasetValidationError: If the data is not a mapping or fails validation.
    """
    where = f" in {source}" if source is not None else ""

    if not isinstance(data, dict):
        raise DatasetValidationError(
            f"Dataset content{where} must be a mapping, got {type(data).__name__}."
        )

    parametrised = DatasetDefinition[input_model, output_model]
    try:
        return parametrised.model_validate(data)
    except ValidationError as exc:
        raise DatasetValidationError(f"Invalid dataset{where}:\n{exc}") from exc
