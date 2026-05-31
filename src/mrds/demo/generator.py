"""Demo data generator: run specifications and per-run client construction.

The narrative is encoded as a tuple of :class:`DemoRunSpec`s. Each spec controls a
run's accuracy (via ``wrong_count``), token usage (``token_scale``), and simulated
latency. The generator derives the oracle and the misclassified-text set from the
real dataset, so the demo evaluates genuine cases through the real engine.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from mrds.datasets.models import DatasetCase
from mrds.demo.client import DeterministicEmailClient


@dataclass(frozen=True)
class DemoRunSpec:
    """One run in the demo narrative."""

    label: str
    role: str  # "baseline" | "history" | "warning" | "critical"
    wrong_count: int  # number of (last) cases deliberately misclassified
    token_scale: float = 1.0
    latency_ms: float = 12.0


# Chronological narrative (see module/package docs for the story it tells).
DEFAULT_RUNS: tuple[DemoRunSpec, ...] = (
    DemoRunSpec("baseline", "baseline", wrong_count=3, token_scale=1.00, latency_ms=12.0),
    DemoRunSpec("history-1", "history", wrong_count=3, token_scale=1.05, latency_ms=14.0),
    DemoRunSpec("history-2", "history", wrong_count=2, token_scale=0.97, latency_ms=10.0),
    DemoRunSpec("warning", "warning", wrong_count=3, token_scale=1.42, latency_ms=12.0),
    DemoRunSpec("critical", "critical", wrong_count=14, token_scale=1.00, latency_ms=13.0),
)


@dataclass(frozen=True)
class DemoConfig:
    """Configuration for a demo seeding run."""

    feature: str = "email_classifier"
    max_cases: int | None = None  # None = full dataset (covers all categories)
    segment_field: str = "category"
    summary: str = "Customer support email classified for the demo dataset."
    simulate_latency: bool = True
    runs: tuple[DemoRunSpec, ...] = field(default_factory=lambda: DEFAULT_RUNS)


DEFAULT_DEMO_CONFIG = DemoConfig()


def build_oracle(cases: Sequence[DatasetCase]) -> tuple[dict[str, str], list[str]]:
    """Return ``(email_text -> correct category, ordered email_texts)`` for ``cases``."""
    oracle = {case.input.email_text: case.expected_output.category.value for case in cases}
    ordered_texts = [case.input.email_text for case in cases]
    return oracle, ordered_texts


def wrong_texts_for(ordered_texts: Sequence[str], wrong_count: int) -> frozenset[str]:
    """Pick the last ``wrong_count`` texts to misclassify (often the harder cases)."""
    if wrong_count <= 0:
        return frozenset()
    return frozenset(ordered_texts[len(ordered_texts) - wrong_count :])


def build_client(
    spec: DemoRunSpec,
    *,
    oracle: dict[str, str],
    ordered_texts: Sequence[str],
    summary: str,
    simulate_latency: bool,
) -> DeterministicEmailClient:
    """Construct the deterministic client for a single run spec."""
    return DeterministicEmailClient(
        oracle=oracle,
        wrong_texts=wrong_texts_for(ordered_texts, spec.wrong_count),
        summary=summary,
        token_scale=spec.token_scale,
        latency_ms=spec.latency_ms,
        simulate_latency=simulate_latency,
    )
