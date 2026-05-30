"""The scoring framework: apply a feature's scorers to one output.

Thin, feature-agnostic glue over the :class:`~mrds.core.interfaces.Scorer`
protocol. A case passes only if every scorer passes.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from mrds.core.interfaces import Scorer, ScoreResult


def score_case(
    scorers: Sequence[Scorer],
    actual: BaseModel,
    expected: BaseModel,
) -> tuple[list[ScoreResult], bool]:
    """Run every scorer and return the scores plus an overall pass flag.

    A case passes only if there is at least one scorer and all of them pass.
    """
    scores = [scorer.score(actual, expected) for scorer in scorers]
    passed = bool(scores) and all(score.passed for score in scores)
    return scores, passed
