"""Feature-agnostic contracts every feature and scorer must satisfy.

These interfaces are what keep the platform extensible: the evaluation engine,
regression detector, reporting, and CLI all depend only on :class:`Feature` and
:class:`Scorer`, never on any concrete feature. Adding a new feature means
implementing :class:`Feature` and registering it — no core changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class ScoreResult(BaseModel):
    """The outcome of a single scorer grading one output against its expected value."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Scorer name.")
    score: float = Field(ge=0.0, le=1.0, description="Normalised score in [0, 1].")
    passed: bool = Field(description="Whether this scorer considers the output acceptable.")
    detail: str = Field(default="", description="Optional human-readable explanation.")


@dataclass(frozen=True)
class FeatureRunResult:
    """A feature's structured output for one input, plus optional token usage.

    Token usage lets the evaluation engine aggregate cost-related metrics without
    coupling to any provider. Features that cannot report usage leave it at zero.
    """

    output: BaseModel
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@runtime_checkable
class Scorer(Protocol):
    """Grades an actual output against an expected output.

    Scorers are pure and feature-defined; the engine (Sprint 5) simply iterates
    over ``feature.scorers()`` and calls :meth:`score`.
    """

    name: str

    def score(self, actual: BaseModel, expected: BaseModel) -> ScoreResult:
        """Return a :class:`ScoreResult` for ``actual`` vs ``expected``."""
        ...


class Feature(ABC):
    """A pluggable LLM-powered feature under test.

    Concrete features declare their identity (``name``), their dataset family
    (``dataset_ref``), their Pydantic input/output models, how to ``run`` a single
    input, and which scorers grade their output. The email classifier is the first
    implementation; future features (``rag_qa``, ``chatbot``, ``ticket_router``)
    follow exactly the same contract.
    """

    #: Unique feature identifier (e.g. ``"email_classifier"``).
    name: ClassVar[str]
    #: Dataset family this feature is evaluated against (wired up in Sprint 4).
    dataset_ref: ClassVar[str]

    @property
    @abstractmethod
    def input_model(self) -> type[BaseModel]:
        """The Pydantic model describing this feature's input."""

    @property
    @abstractmethod
    def output_model(self) -> type[BaseModel]:
        """The Pydantic model describing this feature's structured output."""

    @abstractmethod
    def run(self, payload: BaseModel) -> BaseModel:
        """Produce a validated structured output for a single input."""

    def run_with_usage(self, payload: BaseModel) -> FeatureRunResult:
        """Run and report token usage.

        The default implementation wraps :meth:`run` with zero usage; features
        backed by an LLM should override this to report real token counts. This
        is additive — existing callers of :meth:`run` are unaffected.
        """
        return FeatureRunResult(output=self.run(payload))

    @abstractmethod
    def scorers(self) -> list[Scorer]:
        """Return the scorers used to grade this feature's outputs."""
