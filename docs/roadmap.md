# Roadmap — Model Regression Detection System

> **Status:** Blueprint (pre-implementation). This roadmap sequences the build of the AI Evaluation Platform described in [architecture.md](architecture.md). No implementation has begun.

This roadmap is optimized for a **solo developer using Claude Code**, with an ordering chosen to minimize rework and deliver a working vertical slice early.

---

## Implementation Order Rationale

The platform is built **inside-out and vertical-slice-first**:

1. **Foundation first** (Sprint 1) so every later sprint has config, logging, package layout, and tooling to build on.
2. **Persistence early** (folded into foundation/eval) because SQLite is the system of record — everything writes to it.
3. **Prompt management before the feature** (Sprint 2 → 3) because the feature consumes a versioned prompt.
4. **Feature + dataset before the engine** (Sprint 3 → 4 → 5) so the engine has something real to run.
5. **Engine before regression/reporting/alerting** (Sprint 5 → 6 → 7 → 8) since those all consume engine output.
6. **Operational surfaces last** (dashboard 9 → CI 10 → Docker 11 → polish 12) once the core produces real, persisted runs.

A runnable **vertical slice** (evaluate one feature end-to-end and persist a run) exists by the end of **Sprint 5** — the highest-risk integration is proven early. Each sprint is sized to be completable in focused Claude Code sessions and leaves the system in a working, testable state.

**Cross-cutting rule for every sprint:** type hints everywhere, Ruff clean, pytest passing with OpenAI mocked, and docstrings on public functions.

---

## Sprint 0 — Architecture

**Goal:** Lock the technical blueprint before writing code.

**Deliverables**
- Complete architecture document with module responsibilities, data flows, schema, and all subsystem designs.
- This roadmap (Sprints 0–12).
- `CLAUDE.md` persistent context for future sessions.

**Files created**
- `docs/architecture.md`
- `docs/roadmap.md`
- `CLAUDE.md`

**Dependencies:** none.

**Success criteria**
- All three documents exist and are internally consistent (module names match across docs).
- Repository structure, feature-registry model, custom-engine + adapter boundary, baseline-promotion workflow, six SQLite tables, CLI command set, and cost controls are all documented.
- No implementation code present.

---

## Sprint 1 — Project Foundation

**Goal:** Stand up a clean, tooled Python 3.11 package with config, logging, and the SQLite system of record skeleton.

**Deliverables**
- Installable `mrds` package with the directory layout from the architecture doc.
- Tooling: `pyproject.toml`, Ruff config, pytest config.
- Layered configuration via Pydantic v2 `Settings` (YAML + env).
- Structured logging with correlation IDs.
- SQLite connection + schema (all six tables) + repository skeleton.
- `.env.example`, `.gitignore`, `README.md` stub.

**Files created**
- `pyproject.toml`, `ruff.toml` (or Ruff section), `.gitignore`, `.env.example`, `README.md`
- `src/mrds/__init__.py`
- `src/mrds/config/settings.py`, `config/settings.yaml`, `config/thresholds.yaml`
- `src/mrds/observability/logging.py`
- `src/mrds/db/connection.py`, `db/schema.sql`, `db/repository.py`, `db/migrations/`
- `src/mrds/core/models.py`, `core/ids.py`, `core/hashing.py`
- `tests/conftest.py`, initial unit tests

**Dependencies:** Sprint 0.

**Success criteria**
- `pip install -e .` works; `mrds` package importable.
- Ruff passes; pytest runs (even if few tests).
- A temp SQLite DB can be created from `schema.sql` with all six tables and FKs.
- `Settings` loads from YAML + env and fails fast on missing required secrets.

---

## Sprint 2 — Prompt Management

**Goal:** Versioned, content-hashed prompt store with a runtime loader/registry.

**Deliverables**
- YAML prompt format (per architecture §8).
- Loader that parses YAML, computes content hash, and upserts `prompt_versions`.
- Registry that resolves the active prompt version for a feature.
- First prompt: `email_classifier/v1.yaml`.

**Files created**
- `prompts/email_classifier/v1.yaml`
- `src/mrds/prompts/loader.py`, `prompts/registry.py`
- `tests/unit/test_prompts.py`

**Dependencies:** Sprint 1 (DB, hashing, models).

**Success criteria**
- Loading a prompt upserts exactly one `prompt_versions` row; identical content does not duplicate.
- Editing prompt content changes the `content_hash`.
- Registry returns the correct active version for `email_classifier`.

---

## Sprint 3 — Email Classifier (First Feature)

**Goal:** Implement the first pluggable feature and the feature-registry contract.

**Deliverables**
- `Feature`, `Scorer`, `ScorerAdapter` interfaces in `core/interfaces.py`.
- Feature registry in `core/registry.py`.
- `email_classifier` feature: input/output Pydantic models, `run()` calling OpenAI (structured output: `category` + `summary`), and feature-specific scorers.
- Feature registration wiring in `features/__init__.py`.

**Files created**
- `src/mrds/core/interfaces.py`, `core/registry.py`
- `src/mrds/features/__init__.py`
- `src/mrds/features/email_classifier/{__init__.py,schema.py,feature.py,scorers.py}`
- `tests/unit/test_email_classifier.py` (OpenAI mocked)

**Dependencies:** Sprints 1–2.

**Success criteria**
- `email_classifier` registers and is discoverable via the registry by name.
- `feature.run()` returns a validated output model; OpenAI is mocked in tests.
- Categorical-match and heuristic summary scorers return correct scores on fixtures.
- No feature-specific code outside `features/`.

---

## Sprint 4 — Golden Dataset

**Goal:** Versioned JSON golden datasets with validation, hashing, and a smoke subset.

**Deliverables**
- JSON dataset format + `.meta.json` (per architecture §9).
- Loader that validates each case against the feature schemas, computes content hash, upserts `dataset_versions`.
- `email_classifier/v1.json` covering all four categories, plus a defined smoke subset.

**Files created**
- `datasets/email_classifier/v1.json`, `datasets/email_classifier/v1.meta.json`
- `src/mrds/datasets/loader.py`
- `tests/unit/test_datasets.py`

**Dependencies:** Sprints 1, 3 (schemas to validate against).

**Success criteria**
- Loading the dataset upserts one `dataset_versions` row with correct `case_count`.
- Invalid cases (schema violations) are rejected with clear errors.
- Smoke subset is selectable and strictly smaller than the full set.

---

## Sprint 5 — Evaluation Engine (Vertical Slice Complete)

**Goal:** Feature-agnostic custom engine that runs a feature end-to-end and persists a run. **First runnable vertical slice.**

**Deliverables**
- `eval/engine.py`: resolve feature/prompt/dataset → run each case → score → aggregate → persist `runs` + `test_results`.
- `eval/metrics.py`: accuracy, per-class precision/recall/F1, latency, token/cost aggregation.
- `eval/judge.py`: optional LLM-as-judge (configurable, off by default).
- `eval/adapters/base.py`: `ScorerAdapter` interface (DeepEval/RAGAS adapters stubbed for the future, optional deps).
- First CLI command: `evaluate`.

**Files created**
- `src/mrds/eval/{engine.py,metrics.py,judge.py}`
- `src/mrds/eval/adapters/{__init__.py,base.py,deepeval.py,ragas.py}` (adapters as future-stubs)
- `src/mrds/cli/{__init__.py,main.py}`, `cli/commands/evaluate.py`
- `tests/integration/test_engine.py`

**Dependencies:** Sprints 1–4.

**Success criteria**
- `mrds evaluate --feature email_classifier --smoke` completes (OpenAI mocked in tests) and writes one `runs` row + N `test_results`.
- Metrics in `metrics_json` match hand-computed expectations on the fixture dataset.
- Engine references no feature by name; it works purely through the registry.
- Core engine imports zero third-party eval libraries.

---

## Sprint 6 — Regression Detection

**Goal:** Compare candidate runs to baselines, detect regressions, and implement the baseline-promotion workflow.

**Deliverables**
- `regression/thresholds.py`: threshold model (absolute/relative, warning/critical) loaded from `config/thresholds.yaml`.
- `regression/detector.py`: candidate-vs-baseline comparison producing `regressions` rows.
- CLI `compare` (gate exit code: 1 on critical) and `promote-baseline`.
- Baseline lifecycle in repository (one active baseline per feature).

**Files created**
- `src/mrds/regression/{detector.py,thresholds.py}`
- `src/mrds/cli/commands/{compare.py,promote_baseline.py}`
- `tests/unit/test_regression.py`, `tests/integration/test_compare_promote.py`

**Dependencies:** Sprint 5.

**Success criteria**
- With no baseline, `compare` reports "no baseline" and exits 0.
- A metric drop past a critical threshold yields a `regressions` row and `compare` exits 1.
- A drop past only a warning threshold exits 0 but records the regression.
- `promote-baseline` sets the run as the single active baseline; previous baseline deactivated.

---

## Sprint 7 — Reporting

**Goal:** Human-readable run + comparison reports.

**Deliverables**
- `reporting/builder.py`: build report context from a run and its comparison.
- Jinja2 HTML + Markdown templates (metrics, per-class table, regression table, failure drilldown, cost/latency).
- CLI `report`.

**Files created**
- `src/mrds/reporting/builder.py`
- `src/mrds/reporting/templates/{report.html.j2,report.md.j2}`
- `src/mrds/cli/commands/report.py`
- `tests/unit/test_reporting.py`

**Dependencies:** Sprints 5–6.

**Success criteria**
- `mrds report --run <id>` writes `reports/<feature>/<run_uuid>.html` and `.md`.
- Report shows metrics, any regressions with deltas/severity, and failing cases.
- Rendering is deterministic and unit-tested against a seeded run.

---

## Sprint 8 — Slack Alerting

**Goal:** Notify Slack on regressions and baseline promotions.

**Deliverables**
- `alerting/slack.py`: webhook client (URL from secret).
- `alerting/messages.py`: Block Kit templates for critical/warning regression and promotion.
- Wiring so `compare`/`promote-baseline` emit alerts; failures are best-effort and never change exit codes.

**Files created**
- `src/mrds/alerting/{slack.py,messages.py}`
- `tests/unit/test_alerting.py`

**Dependencies:** Sprints 6–7.

**Success criteria**
- Message payloads built correctly for each trigger (unit-tested; HTTP mocked).
- A webhook failure logs an error but does not alter the gate decision.
- No webhook URL committed; read from env/secret only.

---

## Sprint 9 — Dashboard

**Goal:** Streamlit dashboard over the SQLite system of record.

**Deliverables**
- Multipage Streamlit app reading `eval.db` (read-only): Runs, Trends, Regressions, Baselines.

**Files created**
- `src/mrds/dashboard/app.py`
- `src/mrds/dashboard/pages/{1_runs.py,2_trends.py,3_regressions.py,4_baselines.py}`

**Dependencies:** Sprints 5–8 (real persisted runs to display).

**Success criteria**
- `streamlit run dashboard/app.py` launches all four pages.
- Runs page lists/filter runs; Trends shows metric time-series; Regressions shows deltas/severity; Baselines shows active baseline + history.
- Dashboard performs no model calls and no destructive writes.

---

## Sprint 10 — GitHub Actions

**Goal:** Turn the CLI into a deployment-safety gate in CI.

**Deliverables**
- `ci.yml`: Ruff + pytest on every push/PR.
- `eval.yml`: path-filtered regression gate — `evaluate → compare → report`, artifact upload, Slack notify, fail on critical regression; nightly full run; optional auto-promote on green `main`.

**Files created**
- `.github/workflows/ci.yml`
- `.github/workflows/eval.yml`

**Dependencies:** Sprints 5–8.

**Success criteria**
- `ci.yml` runs lint + tests and blocks on failure.
- `eval.yml` triggers on prompt/dataset/feature/config changes, runs the same CLI, uploads reports, notifies Slack.
- A critical regression fails the job and **blocks the merge**; PRs use the smoke subset.
- Secrets sourced from GitHub Actions secrets.

---

## Sprint 11 — Dockerization

**Goal:** Reproducible image for CLI and dashboard.

**Deliverables**
- `Dockerfile` (Python 3.11 slim, non-root, CLI default entrypoint).
- `docker-compose.yml` with `cli` and `dashboard` services sharing `data/`.

**Files created**
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

**Dependencies:** Sprints 5–9.

**Success criteria**
- Image builds; `docker compose run cli mrds evaluate ...` works.
- `docker compose up dashboard` serves the Streamlit app.
- No secrets baked into the image; passed via environment.

---

## Sprint 12 — Final Polish

**Goal:** Production-quality finish and portfolio readiness.

**Deliverables**
- Complete `README.md` (overview, quickstart, CLI reference, screenshots/gifs).
- A second feature scaffold (e.g. `ticket_router`) to **prove extensibility** with no core changes.
- Coverage pass to targets; Ruff clean repo-wide; docstrings complete.
- End-to-end demo walkthrough documented.

**Files created**
- Full `README.md`
- `src/mrds/features/ticket_router/...` (+ its prompt and dataset) as an extensibility demonstration
- Additional tests to hit coverage targets

**Dependencies:** all prior sprints.

**Success criteria**
- A newcomer can clone, configure `.env`, and run an evaluation + view the dashboard from the README alone.
- Adding the second feature required **zero** changes to `eval/`, `regression/`, `reporting/`, `alerting/`, `db/`, or `cli/`.
- Coverage targets met; CI green.

---

## Milestone Summary

| Milestone | After Sprint | Capability |
|-----------|--------------|------------|
| Tooled skeleton | 1 | Package, config, logging, DB schema |
| Versioned inputs | 2–4 | Prompts + datasets + first feature |
| **Vertical slice** | **5** | Evaluate end-to-end, persist a run |
| Quality gate | 6 | Regression detection + baselines |
| Human surfaces | 7–9 | Reports, Slack, dashboard |
| Deployment safety | 10–11 | CI gate + Docker |
| Portfolio-ready | 12 | Docs + proven extensibility |
