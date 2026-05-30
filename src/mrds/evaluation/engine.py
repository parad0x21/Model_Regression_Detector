"""The evaluation engine — the core execution loop.

Feature-, prompt-, and dataset-agnostic. Given an :class:`EvaluationConfig` it:

1. loads the feature from the Feature Registry,
2. resolves the prompt version from the Prompt Registry (for reproducibility),
3. loads the dataset from the Dataset Registry,
4. executes every case through ``feature.run_with_usage``,
5. applies the feature's scorers,
6. aggregates metrics, and
7. returns a rich :class:`EvaluationResult`.

No persistence happens here — that is a later sprint. A failing case is recorded
as an errored result and never aborts the run.
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from mrds.config.settings import get_settings
from mrds.core.interfaces import Feature
from mrds.core.registry import FeatureRegistry, feature_registry
from mrds.datasets.loader import DEFAULT_DATASETS_DIR
from mrds.datasets.models import DatasetCase
from mrds.datasets.registry import DatasetRegistry
from mrds.evaluation.config import EvaluationConfig
from mrds.evaluation.errors import EvaluationError
from mrds.evaluation.metrics import aggregate
from mrds.evaluation.models import CaseResult, EvaluationResult
from mrds.evaluation.scoring import score_case
from mrds.observability.logging import bind_run_id, get_logger
from mrds.prompts.loader import DEFAULT_PROMPTS_DIR
from mrds.prompts.registry import PromptRegistry

logger = get_logger(__name__)


class EvaluationEngine:
    """Executes a feature against a versioned dataset using a versioned prompt.

    The three registries are injectable; by default the global feature registry is
    used and prompt/dataset registries are built from the conventional directories.
    """

    def __init__(
        self,
        *,
        features: FeatureRegistry | None = None,
        prompts: PromptRegistry | None = None,
        datasets: DatasetRegistry | None = None,
    ) -> None:
        self._features = features or feature_registry
        self._prompts = prompts
        self._datasets = datasets

    def run(self, config: EvaluationConfig) -> EvaluationResult:
        """Run an evaluation and return a structured result."""
        feature = self._features.get(config.feature)
        prompts = self._prompts or PromptRegistry.from_directory(DEFAULT_PROMPTS_DIR)
        datasets = self._datasets or DatasetRegistry.from_directory(DEFAULT_DATASETS_DIR)

        prompt = (
            prompts.get(config.feature, config.prompt_version)
            if config.prompt_version
            else prompts.get_latest(config.feature)
        )
        dataset = (
            datasets.get(config.feature, config.dataset_version)
            if config.dataset_version
            else datasets.get_latest(config.feature)
        )

        cases = list(dataset.definition.cases)
        if config.max_cases is not None:
            cases = cases[: config.max_cases]
        if not cases:
            raise EvaluationError(f"No cases to evaluate for feature '{config.feature}'")

        scorer_names = [scorer.name for scorer in feature.scorers()]
        model = get_settings().model
        run_id = self._new_run_id()

        with bind_run_id(run_id):
            logger.info(
                "Starting evaluation %s: feature=%s prompt=%s dataset=%s cases=%d",
                run_id,
                feature.name,
                prompt.identity,
                dataset.identity,
                len(cases),
            )
            start_time = datetime.now(UTC)
            t0 = perf_counter()
            case_results = [self._run_case(feature, case) for case in cases]
            duration = perf_counter() - t0
            end_time = datetime.now(UTC)

            metrics = aggregate(
                case_results, scorer_names=scorer_names, segment_field=config.segment_field
            )
            logger.info(
                "Completed %s in %.2fs: pass_rate=%.3f passed=%d failed=%d errored=%d",
                run_id,
                duration,
                metrics.pass_rate,
                metrics.passed,
                metrics.failed,
                metrics.errored,
            )

        return EvaluationResult(
            run_id=run_id,
            feature=feature.name,
            prompt_version=prompt.version,
            prompt_hash=prompt.content_hash,
            dataset_version=dataset.version,
            dataset_hash=dataset.content_hash,
            model=model,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            aggregate_metrics=metrics,
            per_case_results=case_results,
        )

    # -- helpers ----------------------------------------------------------------

    @staticmethod
    def _new_run_id() -> str:
        from mrds.core.ids import new_run_id

        return new_run_id()

    def _run_case(self, feature: Feature, case: DatasetCase) -> CaseResult:
        input_dump = case.input.model_dump(mode="json")
        expected_dump = case.expected_output.model_dump(mode="json")
        t0 = perf_counter()
        try:
            run_result = feature.run_with_usage(case.input)
            latency_ms = (perf_counter() - t0) * 1000
            actual = run_result.output
            scores, passed = score_case(feature.scorers(), actual, case.expected_output)
            logger.debug("case %s: passed=%s", case.id, passed)
            return CaseResult(
                case_id=case.id,
                expected_difficulty=case.expected_difficulty,
                input=input_dump,
                expected_output=expected_dump,
                actual_output=actual.model_dump(mode="json"),
                scores=scores,
                passed=passed,
                latency_ms=latency_ms,
                input_tokens=run_result.input_tokens,
                output_tokens=run_result.output_tokens,
                total_tokens=run_result.total_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - one bad case must not abort the run
            latency_ms = (perf_counter() - t0) * 1000
            logger.error("case %s errored: %s", case.id, exc)
            return CaseResult(
                case_id=case.id,
                expected_difficulty=case.expected_difficulty,
                input=input_dump,
                expected_output=expected_dump,
                actual_output=None,
                scores=[],
                passed=False,
                latency_ms=latency_ms,
                error=str(exc),
            )
