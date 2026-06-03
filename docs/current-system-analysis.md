# Current System Analysis (Phase 1 — System Discovery)

> **Status:** Discovery only. No code was modified to produce this document.
> **Date:** 2026-06-02
> **Scope:** The Streamlit dashboard and the data/evaluation layers it reads from.
> **Authoritative design:** [architecture.md](architecture.md). This document
> describes *what exists today* and where the explainability/usability gaps are, as
> input to the product audit (Phase 2) and gap analysis (Phase 3).

---

## 1. Architecture Overview

MRDS is a Python 3.11 package (`src/mrds/`) with a **CLI-first core** and a thin,
**read-only Streamlit dashboard** layered on top. The dashboard never writes; it is
a presentation view over the same SQLite system-of-record the CLI populates.

### 1.1 Frontend structure (the dashboard)

A Streamlit *multipage* app under [src/mrds/dashboard/](../src/mrds/dashboard/):

| File | Role |
|------|------|
| [app.py](../src/mrds/dashboard/app.py) | Home page: title, the "safety net" framing, feature count, links to pages. |
| [pages/1_Runs.py](../src/mrds/dashboard/pages/1_Runs.py) | Browse runs for a feature; drill into one run's metrics/segments/per-case table. |
| [pages/2_Trends.py](../src/mrds/dashboard/pages/2_Trends.py) | Metric time-series (pass rate, scorer means, latency, tokens) across runs. |
| [pages/3_Regressions.py](../src/mrds/dashboard/pages/3_Regressions.py) | Persisted regressions for a selected candidate run. |
| [pages/4_Baselines.py](../src/mrds/dashboard/pages/4_Baselines.py) | Active baseline + promotion history. |
| [_shared.py](../src/mrds/dashboard/_shared.py) | Shared helpers: cached data accessor, feature selector, page-help renderer, demo seeding. |
| [data.py](../src/mrds/dashboard/data.py) | **Streamlit-free** read seam: `DashboardData` wraps `EvaluationStore`; defines `TrendPoint`. |
| [help_text.py](../src/mrds/dashboard/help_text.py) | All plain-English copy (`PAGE_HELP`), Streamlit-free. |

**Key frontend patterns:**

- **`get_data()` is `@st.cache_resource`** — one process-wide `EvaluationStore`
  (SQLite opened `check_same_thread=False`) shared across reruns. Read-only by design.
- **Demo mode:** when `MRDS_DEMO` is truthy *and* the DB has no runs, deterministic
  offline demo data is seeded once (5 runs telling a baseline→warning→critical story).
  See [demo/seed.py](../src/mrds/demo/seed.py).
- **Page help lives in the sidebar** (`render_page_help`) so explanations stay
  visible while the main column scrolls.
- Each page is an independent Streamlit script; cross-widget state is via
  `st.selectbox(..., key=...)`. **There is no shared selection state across pages.**

### 1.2 Backend structure (the core platform)

The dashboard reads from a layered, feature-agnostic core:

```
cli/         evaluate · compare · report · promote-baseline  (same code local + CI)
core/        Feature/Scorer interfaces, registry, ids (run_id = uuid4 hex), hashing
features/    email_classifier (the ONLY feature-specific code)
prompts/     versioned prompt YAML loader/registry
datasets/    versioned golden JSON loader/registry
evaluation/  engine, metrics (pure), scoring, models (EvaluationResult, AggregateMetrics)
regression/  detector (dynamic metric flattening), thresholds, promotion
reporting/   Jinja2 report builder
alerting/    Slack notifier
db/          SQLite connection, schema.sql, repositories, EvaluationStore facade
config/      Pydantic Settings
observability/ structured logging
demo/        deterministic offline seed for the dashboard
```

The dashboard depends only on `db.EvaluationStore`, the `evaluation.models`, and
`db.records` — i.e. the same system-of-record API the CLI uses.

### 1.3 Data flow

```
CLI evaluate ─► EvaluationEngine.run() ─► EvaluationResult (in memory)
                                            │
                          EvaluationStore.save_evaluation()
                                            ▼
                      SQLite: runs (+ metrics_json snapshot)
                              test_results (per-case JSON)
                              prompt_versions / dataset_versions
                                            ▲
                          DashboardData (read-only queries)
                                            ▲
                  Streamlit pages (st.dataframe / st.line_chart / st.metric)
```

CLI `compare` / `promote-baseline` write `regressions` / `baselines` rows. The
dashboard only ever reads.

### 1.4 Evaluation flow (how a run is produced)

[evaluation/engine.py](../src/mrds/evaluation/engine.py):

1. Resolve feature (registry), prompt version (registry), dataset version (registry).
2. For each dataset case: `feature.run_with_usage(input)` → structured output +
   token usage; apply the feature's scorers via `score_case`; record latency.
   A case that raises is captured as an **errored** `CaseResult` (never aborts the run).
3. `aggregate()` ([metrics.py](../src/mrds/evaluation/metrics.py)) computes
   `AggregateMetrics`: pass/fail/error counts, per-scorer stats, per-segment stats
   (by `category`), latency distribution (mean/p50/p95/max), token totals.
4. Return an immutable `EvaluationResult` (run_id, versions, hashes, model, timings,
   aggregate metrics, per-case results).

**Regression detection** ([regression/detector.py](../src/mrds/regression/detector.py)):
`flatten_metrics()` turns `AggregateMetrics` into a flat `name → value` map
(`pass_rate`, `errored`, `latency.*`, `tokens.*`, `scorer.<name>.*`,
`segment.<seg>.<scorer>`). Each shared metric is compared baseline vs candidate,
classified by *kind* (quality/latency/tokens/errors), and assigned a severity
(`pass`/`warning`/`critical`) plus a human-readable **`reason`** string.

### 1.5 Storage strategy

- **SQLite is the system of record** (`data/eval.db`, git-ignored). Schema in
  [db/schema.sql](../src/mrds/db/schema.sql), bootstrapped idempotently via
  `PRAGMA user_version` (`SCHEMA_VERSION = 1`).
- **Two-tier run storage:** the `runs` row carries a **`metrics_json` snapshot**
  (the full `AggregateMetrics`) for cheap reads (trends use only this), while
  `test_results` holds the heavy **per-case JSON** (input/expected/actual/scores).
- **Content-hash identity:** prompts and datasets are keyed by `content_hash`
  (`ON CONFLICT DO NOTHING`), so versions are immutable and deduplicated.
- All writes go through `EvaluationStore`, which wraps related inserts in one
  transaction. Reads reconstruct domain objects (`get_evaluation_result` rebuilds a
  full `EvaluationResult` including every per-case `ScoreResult`).

---

## 2. Existing Pages

> Note on terminology: the prompt's "KPIs page" does **not** exist as a separate
> page. KPIs are the `st.metric` tiles on **Home** ("Features under test") and on
> the **Runs** drill-down (Pass rate / Passed / Failed / Errored).

### 2.1 Home ([app.py](../src/mrds/dashboard/app.py))

- **Purpose:** Orient a first-time visitor; list features under test; route to pages.
- **Current functionality:** Title + caption; an `st.info` "safety net" analogy;
  sidebar page-guide; `st.metric("Features under test", N)`; a bullet per feature
  with its run count.
- **Data sources:** `DashboardData.features()`, `.runs(feature)`.
- **Strengths:** Strong plain-English framing; good "what is this?" onboarding.
- **Weaknesses:** No **business context** for the feature itself (what the email
  classifier *does*, who relies on it, what the categories mean). No headline health
  signal (is the system currently green/red?). The metric is just a count.

### 2.2 Runs ([pages/1_Runs.py](../src/mrds/dashboard/pages/1_Runs.py))

- **Purpose:** Browse historical runs; inspect one run in depth.
- **Current functionality:**
  - A `st.dataframe` of runs showing **`run_id` (raw 32-char UUID)**, status,
    triggered_by, started_at, tokens.
  - A `st.selectbox` of raw UUIDs to pick a run.
  - For the selected run: 4 `st.metric` tiles (pass rate, passed, failed, errored);
    a caption with prompt/dataset/model/duration; a **scorer metrics** table
    (name, mean_score, pass_rate); a **segment metrics** table (by category);
    a **per-case** table (case, difficulty, passed, latency_ms, tokens, error).
- **Data sources:** `data.runs(feature)` (lightweight `RunRecord`s) for the list;
  `data.run_detail(uuid)` (full reconstructed `EvaluationResult`) for the drill-down.
- **Strengths:** The per-run drill-down is genuinely rich; segment metrics already
  expose per-category strength/weakness.
- **Weaknesses:**
  - **Run identity is an opaque UUID** in both the table and the picker.
  - The per-case table shows *that* a case passed/failed but **not why** — the
    `actual_output` vs `expected_output` and the per-scorer `detail` strings are
    persisted but **not displayed**.
  - No way to filter to just failures, sort, or search.
  - The runs list row (`RunRecord`) does not carry the prompt/dataset **version
    strings** — only FK ids — so a human-readable label on the list view needs a
    join or per-run reconstruction (see §5 Risks).

### 2.3 Trends ([pages/2_Trends.py](../src/mrds/dashboard/pages/2_Trends.py))

- **Purpose:** Show whether quality/speed/cost is improving or sliding over runs.
- **Current functionality:** Builds a DataFrame from `TrendPoint`s and renders four
  `st.line_chart`s: pass rate, scorer means, latency (mean + p95), token usage.
  X-axis is **`run_uuid[:8]`** (truncated UUID).
- **Data sources:** `data.trend(feature)` — parses each run's `metrics_json` snapshot
  (cheap; no per-case reads).
- **Strengths:** Efficient (snapshot-only); the right four metric families; clear
  per-chart subheaders.
- **Weaknesses:** X-axis labels are truncated UUIDs (not dates or readable names);
  charts are not clickable (no drill-through to the run); no annotation of *which*
  run was the baseline or where a regression/promotion happened; no explanation of
  *why* a line stepped between two adjacent runs.

### 2.4 Regressions ([pages/3_Regressions.py](../src/mrds/dashboard/pages/3_Regressions.py))

- **Purpose:** Show, for a chosen candidate run, the metrics that regressed vs baseline.
- **Current functionality:** Feature + run selectbox (raw UUIDs); a table of
  persisted regressions: metric, baseline, candidate, delta, severity, detected_at.
  `st.success("No regressions…")` when clean.
- **Data sources:** `data.regressions_for_run(uuid)` → `RegressionRecord`s.
- **Strengths:** Directly answers "did this run regress, and how badly?"; severity
  is the same signal that blocks CI.
- **Weaknesses:**
  - The detector computes a human-readable **`reason`** per comparison, but the
    persisted `RegressionRecord` **drops it** — only the numbers/severity survive.
    So the page cannot explain the regression in words even though the engine did.
  - Only shows **regressed** metrics (severity ≠ pass), never the full comparison,
    so "what stayed fine" is invisible.
  - No link from a regressed metric to the *cases* that caused it.
  - Which baseline this was compared against is not surfaced (only stored as an id).

### 2.5 Baselines ([pages/4_Baselines.py](../src/mrds/dashboard/pages/4_Baselines.py))

- **Purpose:** Show the current trusted "known-good" run and the promotion history.
- **Current functionality:** Active baseline (run UUID, promoted_by, promoted_at,
  optional note); a `st.dataframe` of promotion history (id, run_uuid, active,
  promoted_by, promoted_at, note).
- **Data sources:** `data.active_baseline(feature)`, `data.baseline_history(feature)`,
  `data.run_uuid_for(run_db_id)`.
- **Strengths:** Clear audit trail of when the quality bar moved and by whom.
- **Weaknesses:** Identifies baselines by raw UUID; shows no *metrics* for the
  baseline run (you can't see what quality the bar actually represents without
  going to Runs); no one-click "compare current run to this baseline".

---

## 3. Data Model

SQLite schema ([db/schema.sql](../src/mrds/db/schema.sql)); typed row carriers in
[db/records.py](../src/mrds/db/records.py); domain models in
[evaluation/models.py](../src/mrds/evaluation/models.py).

### 3.1 Runs (`runs` table → `RunRecord`)

| Column | Notes |
|--------|-------|
| `id` | INTEGER PK (internal). |
| `run_uuid` | **uuid4 hex, 32 chars, UNIQUE** — the user-facing id today. |
| `feature_name` | e.g. `email_classifier`. |
| `prompt_version_id` / `dataset_version_id` | FK → version tables (not version *strings*). |
| `model` | e.g. the configured model. |
| `judge_enabled`, `status`, `git_sha`, `triggered_by` | run metadata. |
| `started_at` / `finished_at` / `duration_seconds` | ISO-8601 strings + float. |
| `total_tokens`, `total_cost_usd` | cost proxies (`total_cost_usd` currently 0.0). |
| `metrics_json` | **Full `AggregateMetrics` snapshot** (the trends/KPI source). |

**Run identity available for a human-readable name** (without new columns):
`feature_name`, `model`, `started_at`, plus a join to version tables for
`prompt_version` / `dataset_version` strings, plus a derivable **per-feature
sequence number** (e.g. count of runs with `id <=` this one). All present; the only
missing piece is a stable per-feature ordinal, which is computable from existing rows.

### 3.2 Tests (`test_results` table → `TestResultRecord`)

Per-case rows (FK `run_id`, `ON DELETE CASCADE`): `case_id`,
`expected_difficulty`, **`input_json`**, **`expected_json`**, **`actual_json`**,
`passed`, **`scores_json`** (list of `ScoreResult` dicts), `latency_ms`,
input/output/total tokens, `error`.

> **Explainability data already exists here.** `actual_json` vs `expected_json`
> shows the exact wrong answer; `scores_json` carries each scorer's `detail`
> (e.g. `"expected 'billing', got 'technical'"`). None of this is shown in the UI yet.

### 3.3 Datasets (`dataset_versions` → `DatasetVersionRecord`; files on disk)

`dataset_versions` stores version/`content_hash`/`path`/`case_count`/`created_at`
— **metadata only, not the cases**. The actual golden cases live in
[datasets/email_classifier/v1.json](../datasets/email_classifier/v1.json) (54 cases,
4 categories, with `expected_difficulty` and `notes`). The per-run *snapshot* of
each case's input/expected is also embedded in `test_results`.

### 3.4 Metrics (`AggregateMetrics` in `metrics_json`)

`total_cases`, `passed`, `failed`, `errored`, `pass_rate`;
`scorers: {name → ScorerStats(mean_score, pass_rate, passed, count)}`;
`segments: {segment → SegmentStats(count, passed, pass_rate, scorer_means)}`;
`segment_field` (`category`); `latency: LatencyStats(mean/min/p50/p95/max)`;
`tokens: TokenStats(total/input/output/mean_per_case)`.

### 3.5 Evaluations / Regressions / Baselines

- **`EvaluationResult`** (reconstructable from DB): run_id, feature, prompt/dataset
  version + hash, model, timings, `aggregate_metrics`, `per_case_results`.
- **`regressions`** (`RegressionRecord`): `run_id`, `baseline_run_id`, `metric`,
  `baseline_value`, `candidate_value`, `delta`, `severity`, `detected_at`.
  *(The in-memory `MetricComparison` also has `kind`, `relative_delta`, `regressed`,
  and `reason`, which are **not persisted**.)*
- **`baselines`** (`BaselineRecord`): one active per feature; `run_id`, `is_active`,
  `promoted_by`, `promoted_at`, `note`.
- **`prompt_versions`** (`PromptVersionRecord`): version, content_hash, path.

---

## 4. Existing Reusable Components

**This is the toolbox Phase 5 should build with — favor reuse over new code.**

### 4.1 Data-access seam (no Streamlit dependency)
[dashboard/data.py](../src/mrds/dashboard/data.py) — `DashboardData`:
`features()`, `runs(feature, limit)`, `run_detail(uuid)`,
`regressions_for_run(uuid)`, `active_baseline(feature)`, `baseline_history(feature)`,
`run_uuid_for(db_id)`, `trend(feature)`. **This is the correct place to add new
read queries** (e.g. a run-vs-run comparison, dataset listing) — it is unit-testable
without Streamlit. The underlying `EvaluationStore` already exposes
`get_evaluation_result`, `get_active_baseline_result`, and the per-table repositories.

### 4.2 Shared UI helpers
[dashboard/_shared.py](../src/mrds/dashboard/_shared.py): `get_data()` (cached store),
`feature_selector(data, key=...)`, `render_page_help(page_key)`. New pages should use
these so behavior (caching, demo seeding, help layout) stays consistent.

### 4.3 Help/copy registry
[dashboard/help_text.py](../src/mrds/dashboard/help_text.py): `PAGE_HELP` dict of
`PageHelp(caption, overview, sections)`. **All user-facing explanation copy belongs
here**, Streamlit-free — the natural home for any new "what does this mean?" text.

### 4.4 Layout patterns in use (Streamlit-native, per the guidelines)
`st.metric` (KPI tiles, 4-col layouts), `st.dataframe(use_container_width=True)`
(every table), `st.line_chart` (trends), `st.selectbox(key=...)` (pickers),
`st.columns`, `st.subheader`/`st.markdown`/`st.caption`, sidebar `st.expander`.
**No custom CSS, no components, no charts library beyond Streamlit built-ins +
pandas.** Phase 5 should stay inside this vocabulary (`st.tabs`, `st.expander`,
`st.columns` are the natural next tools).

### 4.5 Domain logic worth reusing (already written, just unused by the UI)
- **Regression `reason` strings** and `MetricComparison.relative_delta` —
  ([detector.py](../src/mrds/regression/detector.py)) computed but not surfaced.
- **`ScoreResult.detail`** per-scorer explanations — persisted in `scores_json`.
- **`RegressionDetector.compare(baseline, candidate)`** — already does an arbitrary
  two-run comparison in memory; a "Run A vs Run B" feature can call it directly with
  two reconstructed `EvaluationResult`s (no new comparison math needed).
- **`flatten_metrics()`** — a ready-made flat metric map for delta tables.

---

## 5. Risks (where changes could break functionality)

Ordered roughly by likelihood of biting an incremental change.

1. **`@st.cache_resource` on `get_data()` is read-only by contract.** The cached
   `EvaluationStore` is shared across reruns/sessions with `check_same_thread=False`.
   Introducing any *write* through it (or long-lived mutable state) risks cross-session
   bleed and threading issues. New features must stay read-only and go through
   `DashboardData`.

2. **Demo seeding only runs on an empty DB.** `seed_demo` short-circuits if any run
   exists. Anything that pre-creates rows (or any test that shares the DB) will
   silently disable demo data. Keep demo and real data paths separate.

3. **Run-list rows lack version strings (N+1 risk).** `RunRecord` carries
   `prompt_version_id`/`dataset_version_id`, not the version *strings*. A
   human-readable run label like "…Dataset v3" on the **list** view needs either a
   join query (preferred — add one method to `DashboardData`/repository) or
   per-run `run_detail()` reconstruction, which is **O(runs)** full reconstructions
   (each reads all per-case rows). Use the lightweight path; do not call
   `run_detail` in a loop.

4. **Frozen Pydantic models.** `EvaluationResult`, `AggregateMetrics`, `CaseResult`,
   `ScoreResult`, the `*Record` rows, `MetricComparison` are all
   `ConfigDict(frozen=True)`. They cannot be mutated in place; derive new views
   rather than editing instances. Changing their fields ripples through the DB
   round-trip (`save_evaluation` / `_reconstruct`) and the test suite.

5. **`run_uuid` is the user-facing key everywhere.** Selectboxes, the regressions
   picker, and baseline display all key off the raw UUID. A human-readable name must
   be **display-only** and preserve `run_uuid` as the internal value behind every
   widget (e.g. label→uuid mapping), or run selection silently breaks. The CLAUDE.md
   contract ("preserve the original run_id internally") makes this a hard requirement.

6. **Schema/contract coupling.** Persisting anything new (e.g. the regression
   `reason`) means a schema change → `SCHEMA_VERSION` bump + migration, and touches
   `RegressionRecord`, `repositories.py`, `store.py`, and their tests. Per
   CLAUDE.md, schema/interface changes must also update
   [architecture.md](architecture.md). Prefer **deriving** explanations at read time
   (recompute via `RegressionDetector`) over new columns where feasible, to avoid a
   migration.

7. **Pages are independent scripts with no shared selection state.** A feature
   selected on Runs does not carry to Regressions. Any cross-page flow (e.g. "compare
   these two runs") must thread state explicitly via `st.session_state`/query params;
   there is no existing mechanism to lean on.

8. **Reconstruction cost for many runs.** `run_detail` / `get_evaluation_result`
   rebuild a full `EvaluationResult` (all per-case rows + JSON parsing). Fine for one
   run; a comparison of two is fine; anything sweeping many runs should use the
   `metrics_json` snapshot path (as `trend()` already does).

9. **Test/CI coverage is the safety net — keep it green.** The CLAUDE.md working
   agreement requires Ruff-clean + pytest-green before any task is done, full type
   hints, and docstrings. The dashboard's `data.py` is the testable seam; new logic
   should land there (with tests) rather than inside page scripts.

---

## 6. Summary: data that already exists but is not yet surfaced

The single most important discovery for Phases 3–5: **most explainability data is
already captured and persisted — the gap is presentation, not pipeline.**

| Desired capability | Data already present? | Where |
|--------------------|----------------------|-------|
| Why a case failed (actual vs expected) | ✅ | `test_results.actual_json` / `expected_json` |
| Per-scorer explanation per case | ✅ | `test_results.scores_json` → `ScoreResult.detail` |
| Why a run regressed (words) | ⚠️ computed, not stored | `MetricComparison.reason` (recomputable via detector) |
| Run-to-run comparison / deltas | ⚠️ logic exists, no UI | `RegressionDetector.compare`, `flatten_metrics` |
| Human-readable run name | ⚠️ derivable | `feature` + `model` + `started_at` + version join + ordinal |
| Dataset contents | ✅ on disk + per-run snapshot | `datasets/<f>/vN.json`, `test_results.input/expected_json` |
| Per-category strengths/weaknesses | ✅ shown | `AggregateMetrics.segments` |
| Business context for the feature | ❌ not captured anywhere | (would be new copy in `help_text.py`) |

This means several roadmap items are **UI-only, low-risk** changes against existing
reads, while a few (persisting regression reasons, business-context copy) need a
small backend or content addition. Phase 3 will size each of these precisely.
