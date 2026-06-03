# Product Gap Analysis (Phase 3)

> **Status:** Analysis only — **no code is written and no roadmap is set** (that is
> Phase 4). This document sizes the gap between today's system and the eleven desired
> capabilities, one block each.
> **Sources of truth:** [current-system-analysis.md](current-system-analysis.md)
> (what exists / where the data lives) and [product-audit.md](product-audit.md)
> (what confuses users).
> **Date:** 2026-06-02.

### Optimization lens (read this first)

Per the brief, this analysis **optimizes for user comprehension and recruiter-demo
quality, not technical completeness.** Concretely that means, when sizing each gap:

- A change that makes a screen *understandable in 30 seconds* outranks a change that
  is technically thorough but invisible to a viewer.
- "Required backend changes" are kept **deliberately minimal** — Phase 1 proved most
  meaning is already stored or computable, so the default posture is *derive at read
  time / surface what exists*, and **avoid schema migrations** unless a capability is
  impossible without one.
- Effort and risk are judged against the project's safety rails (read-only dashboard,
  frozen models, demo seeding, Ruff + pytest gate). "Low risk" means *display-only,
  no schema change, no write path*.

### How to read each block

Every capability has the seven required fields: **Current State · Missing Functionality
· Required Data · Required UI Changes · Required Backend Changes · Estimated Effort ·
Risk Level**, plus two short framing lines — **Comprehension Value** and **Recruiter
Demo Value** — because those are the optimization targets. Effort is in rough
half-day units (S ≈ ≤½ day, M ≈ ~1 day, L ≈ 2-3 days). Risk is Low/Med/High by the
definition above.

### Legend — data readiness (from Phase 1, §6)

- 🟢 **Stored** — the data already sits in SQLite and just isn't shown.
- 🟡 **Computable** — derivable at read time from stored data / existing logic.
- 🔴 **Absent** — not captured anywhere; needs new content or a new write.

---

## 1. Feature Overview Panel

**Comprehension Value:** ★★★★☆ — tells PMs/recruiters *what is actually being tested*.
**Recruiter Demo Value:** ★★★★☆ — turns a slug into a product story on the first screen.

- **Current State:** Home shows `email_classifier — N runs` as a bare slug. No
  description of what the feature does, who relies on it, or what its four categories
  (billing/technical/account/general) mean. The thing under test is invisible as a
  *product* ([product-audit.md](product-audit.md), Home).
- **Missing Functionality:** A short, business-framed panel per feature: one-line
  purpose, what each category/scorer means in plain terms, and a current health
  verdict (healthy / warning / blocked) with headline counts (runs, current pass rate,
  regressions caught).
- **Required Data:** 🔴 **Absent** for the *prose* (purpose, category meanings — must
  be authored). 🟢 **Stored** for the *stats* (run count, latest pass rate via
  `metrics_json`, regression counts). 🟡 **Computable** for the health verdict
  (latest run's regression severity).
- **Required UI Changes:** An overview block on Home (and optionally a header on each
  page) using `st.metric` + `st.markdown`. No new page required.
- **Required Backend Changes:** None to the schema. New **copy** belongs in
  `help_text.py` (Phase 1's designated home for explanation text); a small read helper
  on `DashboardData` to assemble the headline stats. The feature-description text can
  be a static mapping keyed by feature name (feature-agnostic: features without copy
  fall back to the slug).
- **Estimated Effort:** **S–M.** Mostly writing good copy + one read helper + one
  layout block.
- **Risk Level:** **Low.** Display-only, additive, no schema/write changes.

---

## 2. Human-Readable Run Names

**Comprehension Value:** ★★★★★ — the single most universally-felt gap (all five personas).
**Recruiter Demo Value:** ★★★★★ — makes every screen look like a product, not a DB dump.

- **Current State:** Runs are identified by a raw 32-char uuid4 hex everywhere — the
  runs table lead column, every `st.selectbox`, the Trends x-axis (`run_uuid[:8]`),
  and the Baselines display.
- **Missing Functionality:** A friendly label such as
  **"Email Classifier #12 · model · dataset v1 · Jun 2, 2026"**, shown in tables,
  pickers, and chart axes — while the internal `run_uuid` remains the value behind
  every widget.
- **Required Data:** 🟡 **Computable.** Phase 1 confirmed all parts exist: `feature`,
  `model`, `started_at` are on `RunRecord`; the dataset/prompt **version strings** come
  from a join to the version tables; the **per-feature sequence number** ("#12") is
  derivable from run ordering. No new columns needed.
- **Required UI Changes:** Replace raw-UUID display in all four pages with the label;
  pickers use a `label → run_uuid` mapping so selection still resolves to the UUID.
- **Required Backend Changes:** One read-side helper (ideally on `DashboardData`) that
  returns a `(run_uuid, display_label)` view for a feature's runs — built from a
  **lightweight join**, *not* per-run `run_detail()` reconstruction (Phase 1, §5 Risk 3:
  avoid the N+1). Pure label formatting; no schema change.
- **Estimated Effort:** **M.** The helper is small; the cost is touching all four pages
  consistently and the label↔uuid mapping in each picker.
- **Risk Level:** **Med.** Display-only, but `run_uuid` is the key behind every
  selector (Phase 1, §5 Risk 5) — the label must stay strictly cosmetic or run
  selection silently breaks. Well-covered by tests on the new helper.

---

## 3. Failure Explanations

**Comprehension Value:** ★★★★★ — fulfills the platform's core promise (explainability).
**Recruiter Demo Value:** ★★★★★ — "it shows the model's wrong answer" is a demo moment.

- **Current State:** The per-case table shows `passed = False` and nothing about *why*.
  Phase 1 confirmed the wrong answer and the reason are **already stored** and simply
  not displayed.
- **Missing Functionality:** For a failing case: the model's **actual output** vs the
  **expected output**, and each scorer's **`detail`** string
  (e.g. *"expected 'billing', got 'technical'"*), plus the original input email.
- **Required Data:** 🟢 **Stored.** `test_results.actual_json`, `expected_json`,
  `input_json`, and `scores_json` (→ `ScoreResult.detail`) all persist this; the
  reconstructed `EvaluationResult.per_case_results` already carries it into the
  dashboard.
- **Required UI Changes:** On Runs, an expandable per-failing-case view
  (`st.expander` per case, or a "failures only" filter) showing input · expected ·
  actual · per-scorer reason. Native widgets only.
- **Required Backend Changes:** **None.** `run_detail()` already returns everything;
  this is pure presentation of data already in hand.
- **Estimated Effort:** **S–M.** A formatting/layout task over existing reconstructed
  data.
- **Risk Level:** **Low.** Display-only, no schema/write, no new query.

---

## 4. Pass Explanations

**Comprehension Value:** ★★★☆☆ — reassures and teaches what "good" looks like.
**Recruiter Demo Value:** ★★★☆☆ — nice symmetry with failure explanations; secondary.

- **Current State:** A passing case shows `passed = True` with no detail. The same
  per-scorer `detail` strings exist for passes too (e.g. *"category matched"*,
  *"words=14, sentences=1"*) but aren't shown.
- **Missing Functionality:** For a passing case (on demand), the per-scorer reasons
  that *earned* the pass — so a viewer understands the bar, not just the verdict.
- **Required Data:** 🟢 **Stored.** Identical source to Failure Explanations
  (`scores_json` → `ScoreResult.detail`), already reconstructed.
- **Required UI Changes:** The *same* expandable per-case view as item 3, simply also
  available for passing cases (kept collapsed by default to keep failures front-and-center).
- **Required Backend Changes:** **None** — shares item 3's data path entirely.
- **Estimated Effort:** **S.** Effectively free once item 3 exists (same component).
- **Risk Level:** **Low.** Display-only.

---

## 5. Run Comparison (Run A vs Run B)

**Comprehension Value:** ★★★★☆ — answers the AI engineer's real question directly.
**Recruiter Demo Value:** ★★★★★ — "pick my new prompt vs the old one" is a strong demo.

- **Current State:** No arbitrary two-run comparison exists. The Regressions page only
  shows a candidate vs *its baseline*, via persisted regression rows.
- **Missing Functionality:** Pick any two runs of a feature and see a side-by-side of
  their KPIs, scorer means, and segment performance, with the differences highlighted.
- **Required Data:** 🟡 **Computable.** Phase 1 confirmed
  `RegressionDetector.compare(baseline, candidate)` already performs an arbitrary
  two-run comparison in memory, and `flatten_metrics()` yields a flat metric map for
  diffing. Both runs are reconstructable via `get_evaluation_result`.
- **Required UI Changes:** A comparison view — two run pickers (using the readable
  labels from item 2) and a side-by-side / delta table. Could be a new page or a tab
  on Runs.
- **Required Backend Changes:** A thin read helper on `DashboardData` that reconstructs
  two runs and returns their comparison (reusing the existing detector / flatten
  logic). **Reuses existing comparison math — no new algorithm.** No schema change.
- **Estimated Effort:** **M.** Two reconstructions + a table; the logic already exists.
- **Risk Level:** **Med.** Reconstructing two full runs is fine (Phase 1, §5 Risk 8 —
  two is cheap); the watch-out is keeping it to *two* and not sweeping many runs.
  Cross-page selection state (Risk 7) applies if launched from another page.

---

## 6. Delta Analysis (why scores changed between runs)

**Comprehension Value:** ★★★★☆ — converts "a number moved" into "here's the change."
**Recruiter Demo Value:** ★★★★☆ — quantified deltas read as rigor.

- **Current State:** Regressions shows raw `delta` numbers for regressed metrics only;
  Trends shows movement with no per-step delta or attribution. The computed
  `relative_delta` and per-comparison `reason` are **not surfaced** (Phase 1).
- **Missing Functionality:** A clear "what changed" view between two runs (or
  adjacent trend points): each metric's before → after, absolute and relative delta,
  a good/bad indicator, **and whether the prompt or dataset changed between them**
  (the attribution the PM persona asked for).
- **Required Data:** 🟡 **Computable.** `MetricComparison` already carries `delta`,
  `relative_delta`, `kind`, `severity`, and a `reason`; `RegressionResult` already
  exposes `prompt_changed` / `dataset_changed`. All produced by the existing detector;
  just not all persisted or shown.
- **Required UI Changes:** A delta table (reused inside Run Comparison item 5 and/or
  on Trends as step context): metric · before · after · Δ · Δ% · verdict, plus a
  "prompt/dataset changed" banner.
- **Required Backend Changes:** None to schema — derive at read time via the detector
  (the `reason` and `relative_delta` are recomputed rather than read from a column,
  avoiding a migration per Phase 1, §5 Risk 6). Shares item 5's helper.
- **Estimated Effort:** **S–M.** Mostly presenting `MetricComparison` fields that the
  detector already returns.
- **Risk Level:** **Low–Med.** Display/derive-only; no schema change. Med only if
  fused onto Trends (more surface area).

---

## 7. KPI Drilldowns

**Comprehension Value:** ★★★★☆ — turns a bare number into "what is this and is it good?"
**Recruiter Demo Value:** ★★★☆☆ — supports the "everything is explained" narrative.

- **Current State:** `st.metric` tiles (Home feature count; Runs pass/passed/failed/
  errored) and table columns have no explanation, no units, no good/bad framing, and
  no path to "what's behind this number."
- **Missing Functionality:** Each KPI carries (a) a plain-language definition + units
  in-context, (b) a good/bad verdict (e.g. vs baseline or threshold), and (c) a
  drill-through to the underlying cases/segment behind it.
- **Required Data:** 🟢 **Stored** (the KPI values) + 🟡 **Computable** (the verdict,
  by comparing to the active baseline). 🔴 **Absent**: the definitional copy (author
  once).
- **Required UI Changes:** Help affordances on tiles (`st.metric`'s `help=` /
  `delta=`, captions), threshold/baseline coloring, and a link from a weak segment KPI
  to its cases (ties into items 3 and 10).
- **Required Backend Changes:** None to schema. KPI definition copy → `help_text.py`;
  the baseline-delta verdict reuses the active-baseline read that already exists
  (`active_baseline` / `get_active_baseline_result`).
- **Estimated Effort:** **M.** Spread across several tiles/tables; copy + verdict
  wiring is the bulk.
- **Risk Level:** **Low.** Additive display; the only nuance is computing the
  baseline-delta verdict (read-only).

---

## 8. Full Test Log Explorer

**Comprehension Value:** ★★★★☆ — lets any viewer *browse the evidence* themselves.
**Recruiter Demo Value:** ★★★★☆ — "every example, searchable" demonstrates depth.

- **Current State:** The per-case table on Runs lists cases (case/difficulty/passed/
  latency/tokens/error) for one run, but cannot filter to failures, search text, sort,
  or show the input/expected/actual payloads.
- **Missing Functionality:** A complete, filterable case explorer for a run: search by
  text, filter by pass/fail/error · category · difficulty, sort by latency/tokens, and
  expand any case to its full input/expected/actual/scores (item 3's detail).
- **Required Data:** 🟢 **Stored.** All per-case fields are in `test_results` and
  already reconstructed into `per_case_results` (input/expected/actual/scores/
  difficulty/latency/tokens/error).
- **Required UI Changes:** A richer `st.dataframe` (column config, sortable) plus
  filter controls (`st.selectbox`/`st.multiselect`/text input) and the per-case
  expander. Could live on Runs or as its own page/tab.
- **Required Backend Changes:** None to schema. Optionally a `DashboardData` helper to
  return per-case rows in a filter-friendly shape (still from existing reconstruction).
- **Estimated Effort:** **M.** UI-heavy (filters/sort), data already available.
- **Risk Level:** **Low.** Display-only over data already loaded for one run.

---

## 9. Dataset Explorer

**Comprehension Value:** ★★★★☆ — answers "what is the model actually being tested on?"
**Recruiter Demo Value:** ★★★★☆ — the hand-labeled golden set is a credibility asset.

- **Current State:** `dataset_versions` stores only metadata (version/hash/case_count/
  path). The actual 54 golden cases live in `datasets/email_classifier/v1.json`
  (with `expected_difficulty` and human `notes`) and are not viewable in the UI.
- **Missing Functionality:** A view of the golden dataset: its description, case count,
  category and difficulty distribution, and a browsable/searchable list of cases
  (input · expected · difficulty · notes).
- **Required Data:** 🟢/🟡 **Available two ways:** the on-disk versioned JSON (richest —
  includes `notes` and the dataset `description`), or the per-run snapshot embedded in
  `test_results` (`input_json`/`expected_json`). The dataset loader/registry already
  exists to read the files.
- **Required UI Changes:** A Dataset page/section: header (description, counts,
  distributions via `st.metric` + a small chart) and a searchable `st.dataframe` of
  cases.
- **Required Backend Changes:** None to schema. A `DashboardData`/loader read that
  surfaces dataset cases for a feature (reusing `DatasetRegistry`). Decide source
  (disk file vs per-run snapshot); disk is richer for the demo.
- **Estimated Effort:** **M.** New view + a read that reuses the existing loader.
- **Risk Level:** **Low.** Read-only; the only choice is data source. Note: reading the
  on-disk file is outside the SQLite read path (minor consistency consideration, not a
  risk to existing behavior).

---

## 10. Root Cause Analysis

**Comprehension Value:** ★★★★★ — closes the loop from "a metric regressed" to "these cases."
**Recruiter Demo Value:** ★★★★★ — the "click the red metric → see the exact failures" arc.

- **Current State:** Regressions shows *that* a metric fell; nothing links a regressed
  metric to the specific cases that caused it. The plain-English `reason` is computed
  and then discarded before display (Phase 1, §5 Risk 6 / §6).
- **Missing Functionality:** For a regression: the human-readable reason in words,
  **plus** a drill from the regressed metric (e.g. `category_match` in the `account`
  segment) to the failing cases behind it (their input/expected/actual/scores), and a
  one-line impact statement ("this would block the deploy").
- **Required Data:** 🟡 **Computable / mostly stored.** The `reason` and
  `relative_delta` are produced by the detector (recompute at read time). The mapping
  from a regressed metric → cases is derivable: a scorer/segment metric points at the
  cases failing that scorer/in that segment, all present in `per_case_results`.
- **Required UI Changes:** On Regressions, attach the reason text to each row and an
  expander that lists the contributing failing cases (reusing item 3's case detail);
  a clear blocking/non-blocking banner.
- **Required Backend Changes:** None to schema (deliberately — derive the reason via
  the detector rather than persisting it, to avoid a migration). A read helper that,
  given a candidate run + baseline, returns regressions *with* reasons and their
  contributing cases. Reuses `compare()` + `per_case_results`.
- **Estimated Effort:** **M–L.** The reason text is easy; the metric→cases mapping
  (especially for segment/scorer metrics) is the real work and needs careful tests.
- **Risk Level:** **Med.** Derive-only (no schema), but the metric→case attribution
  logic is new and must be correct — it belongs in `DashboardData`/a pure helper with
  unit tests, not in a page script (Phase 1, §5 Risk 9).

---

## 11. Perfect Run Recommendations

**Comprehension Value:** ★★★☆☆ — frames "what would make this green" as guidance.
**Recruiter Demo Value:** ★★★☆☆ — pleasant, but the least essential of the eleven.

- **Current State:** Nothing tells a viewer what a flawless run would require. The data
  to describe the *gap to perfect* exists (failing cases, per-category weak spots,
  thresholds), but no view assembles it.
- **Missing Functionality:** A concise "to reach a perfect/green run" summary: which
  cases must flip to pass, which categories/scorers are dragging the score, and how far
  each metric is from its threshold (and from the baseline).
- **Required Data:** 🟡 **Computable.** Failing cases and per-scorer/per-segment weak
  spots come from `per_case_results` + `AggregateMetrics.segments`; "distance to
  threshold" comes from the existing `ThresholdConfig` + detector logic; "distance to
  baseline" from the active-baseline comparison.
- **Required UI Changes:** A small recommendations panel on a run (or on Regressions):
  a ranked list of "fix these N cases / this category to recover X points," in plain
  language.
- **Required Backend Changes:** None to schema. A read helper that summarizes the gap
  (failing cases by category + threshold/baseline distances) using existing
  metrics/threshold logic. This is the most *derivation*-heavy item.
- **Estimated Effort:** **M–L.** The summarization logic + good plain-language framing
  is the bulk; depends conceptually on items 3 and 10 existing first.
- **Risk Level:** **Med.** Derive-only, but it's interpretive — wording must avoid
  over-promising ("guaranteed perfect"), and the gap math needs tests. Lowest priority
  of the set, highest framing-risk.

---

## Summary Matrix

Ordered as the eleven were given; sorted views are deferred to Phase 4's roadmap.

| # | Capability | Data readiness | Backend (schema) | Effort | Risk | Comprehension | Recruiter demo |
|---|-----------|:--------------:|:----------------:|:------:|:----:|:-------------:|:--------------:|
| 1 | Feature Overview Panel | 🟢🟡 + copy | none | S–M | Low | ★★★★☆ | ★★★★☆ |
| 2 | Human-Readable Run Names | 🟡 | none | M | Med | ★★★★★ | ★★★★★ |
| 3 | Failure Explanations | 🟢 | none | S–M | Low | ★★★★★ | ★★★★★ |
| 4 | Pass Explanations | 🟢 | none | S | Low | ★★★☆☆ | ★★★☆☆ |
| 5 | Run Comparison (A vs B) | 🟡 | none | M | Med | ★★★★☆ | ★★★★★ |
| 6 | Delta Analysis | 🟡 | none | S–M | Low–Med | ★★★★☆ | ★★★★☆ |
| 7 | KPI Drilldowns | 🟢🟡 + copy | none | M | Low | ★★★★☆ | ★★★☆☆ |
| 8 | Full Test Log Explorer | 🟢 | none | M | Low | ★★★★☆ | ★★★★☆ |
| 9 | Dataset Explorer | 🟢🟡 | none | M | Low | ★★★★☆ | ★★★★☆ |
| 10 | Root Cause Analysis | 🟡 | none | M–L | Med | ★★★★★ | ★★★★★ |
| 11 | Perfect Run Recommendations | 🟡 | none | M–L | Med | ★★★☆☆ | ★★★☆☆ |

### Cross-cutting observations (input to Phase 4)

- **No capability requires a schema migration.** Every item can be delivered read-only
  / derive-at-read-time. This is the direct payoff of Phase 1, §6 — the meaning is
  already stored or computable — and it keeps the whole effort in the Low/Med risk band
  against the project's safety rails.
- **A few items are force multipliers.** Item 3 (Failure Explanations) is a shared
  component reused by items 4, 8, 10, and 11 — building it first makes four others
  cheaper. Item 2 (Readable Run Names) is a prerequisite for items 5/6 reading well.
- **The highest comprehension + demo payoff for the effort** clusters in items
  **2, 3, 5, and 10** — all ★★★★★ on at least one axis, all read-only/derive-only.
  These are the natural spine of the roadmap.
- **Item 11 depends on 3 and 10**, has the lowest essential value, and the highest
  framing risk — a natural P2.
- Two recurring **non-capability** gaps surfaced in Phase 2 (a consistent good/bad
  **verdict color** on data; cross-page **selection state**) are not items on this list
  but underpin items 2, 5, 6, 7, and 10. Phase 4 should treat them as small shared
  enablers rather than standalone features.

> **Reminder:** This is sizing, not sequencing. Phase 4 will turn these into a
> prioritized P0/P1/P2 roadmap with an explicit build order, optimizing the same way —
> for comprehension and recruiter-demo impact, not technical completeness.
