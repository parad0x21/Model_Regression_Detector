"""Pure metric aggregation over per-case results.

No I/O, no feature knowledge: aggregation works purely from :class:`CaseResult`
records and a list of scorer names, so it applies to any feature. ``segment_field``
selects an expected-output key to break metrics down by.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

from mrds.evaluation.models import (
    AggregateMetrics,
    CaseResult,
    LatencyStats,
    ScorerStats,
    SegmentStats,
    TokenStats,
)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    """Linear-interpolation percentile (``pct`` in [0, 1]) over a sorted sequence."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * pct
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(sorted_values[int(rank)])
    return sorted_values[low] * (high - rank) + sorted_values[high] * (rank - low)


def _scorer_stats(case_results: Sequence[CaseResult], name: str) -> ScorerStats:
    values: list[float] = []
    passed = 0
    for case in case_results:
        for score in case.scores:
            if score.name == name:
                values.append(score.score)
                passed += 1 if score.passed else 0
    count = len(values)
    return ScorerStats(
        name=name,
        mean_score=_mean(values),
        pass_rate=passed / count if count else 0.0,
        passed=passed,
        count=count,
    )


def _segment_stats(
    items: Sequence[CaseResult], segment: str, scorer_names: Sequence[str]
) -> SegmentStats:
    passed = sum(1 for c in items if c.error is None and c.passed)
    scorer_means = {
        name: _mean([s.score for c in items for s in c.scores if s.name == name])
        for name in scorer_names
    }
    return SegmentStats(
        segment=segment,
        count=len(items),
        passed=passed,
        pass_rate=passed / len(items) if items else 0.0,
        scorer_means=scorer_means,
    )


def aggregate(
    case_results: Sequence[CaseResult],
    *,
    scorer_names: Sequence[str],
    segment_field: str | None = None,
) -> AggregateMetrics:
    """Aggregate per-case results into :class:`AggregateMetrics`."""
    total = len(case_results)
    errored = sum(1 for c in case_results if c.error is not None)
    passed = sum(1 for c in case_results if c.error is None and c.passed)
    failed = total - errored - passed

    scorers = {name: _scorer_stats(case_results, name) for name in scorer_names}

    segments: dict[str, SegmentStats] = {}
    if segment_field is not None:
        groups: dict[str, list[CaseResult]] = defaultdict(list)
        for case in case_results:
            label = str(case.expected_output.get(segment_field, "unknown"))
            groups[label].append(case)
        segments = {
            label: _segment_stats(groups[label], label, scorer_names) for label in sorted(groups)
        }

    latencies = sorted(c.latency_ms for c in case_results)
    latency = LatencyStats(
        count=len(latencies),
        total_ms=sum(latencies),
        mean_ms=_mean(latencies),
        min_ms=latencies[0] if latencies else 0.0,
        p50_ms=_percentile(latencies, 0.50),
        p95_ms=_percentile(latencies, 0.95),
        max_ms=latencies[-1] if latencies else 0.0,
    )

    total_tokens = sum(c.total_tokens for c in case_results)
    tokens = TokenStats(
        total_tokens=total_tokens,
        total_input_tokens=sum(c.input_tokens for c in case_results),
        total_output_tokens=sum(c.output_tokens for c in case_results),
        mean_tokens_per_case=total_tokens / total if total else 0.0,
    )

    return AggregateMetrics(
        total_cases=total,
        passed=passed,
        failed=failed,
        errored=errored,
        pass_rate=passed / total if total else 0.0,
        scorers=scorers,
        segments=segments,
        segment_field=segment_field,
        latency=latency,
        tokens=tokens,
    )
