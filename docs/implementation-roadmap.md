# Implementation Roadmap (Phase 4)

> **Status:** Prioritization and sequencing only — **no code yet.** Phase 5 implements
> **one item at a time, with approval between each.**
> **Sources of truth:** [current-system-analysis.md](current-system-analysis.md),
> [product-audit.md](product-audit.md), [product-gap-analysis.md](product-gap-analysis.md).
> **Date:** 2026-06-02.

### Optimization lens (unchanged)

This roadmap optimizes for **user comprehension and recruiter-demo quality, not
technical completeness.** Sequencing therefore favors:

1. items that make a screen understandable fast,
2. items that produce a visible "demo moment," and
3. shared components that make later items cheaper.

Phase 3 established the enabling fact this plan leans on: **no item requires a schema
migration** — everything is read-only or derive-at-read-time, so the whole roadmap sits
in the Low/Med risk band against the project's safety rails (read-only dashboard,
frozen models, demo seeding, Ruff + pytest gate).

### Priority definitions

- **P0 — Essential.** The dashboard is not demo-credible without it. Fixes a gap felt
  by *every* persona or unlocks the platform's core promise (explainability).
- **P1 — High value.** Strong comprehension/demo payoff; depends on or is amplified by
  P0 work.
- **P2 — Nice to have.** Real but secondary value, or higher framing risk; safe to ship
  last or defer.

### Per-item scorecard fields (as required by the brief)

Every item below lists **User Value · Recruiter Demo Value · Engineering Effort ·
Technical Risk · Dependencies.** Effort uses Phase 3's units (S ≈ ≤½ day, M ≈ ~1 day,
L ≈ 2–3 days).

---

## Two shared enablers (build implicitly inside the first item that needs them)

Phase 3 surfaced two cross-cutting needs that aren't standalone features but underpin
many items. They are **not** scheduled as their own roadmap entries; instead they are
absorbed into the first P0 item that requires them, then reused.

- **E1 — Verdict styling helper.** A tiny, reusable "good / warning / critical → color +
  word" formatter so any number can carry a verdict. Needed by items 2, 3, 6, 7, 10.
  *Built inside Item 1 or 2; lives next to `help_text.py` as Streamlit-free copy + a
  thin render helper.*
- **E2 — Readable-run-label helper.** The `(run_uuid → display label)` view from
  gap-analysis Item 2. This *is* roadmap Item **R1** below (it's substantial enough to
  schedule), and everything else consumes it.

---

## P0 — Essential (the demo-credible core)

> Goal of P0: a recruiter or EM can open the dashboard and, on every screen, (a) tell
> what they're looking at, (b) tell whether it's good or bad, and (c) see *why* a
> failure happened. These four items deliver that.

### R1 — Human-Readable Run Names  *(gap item 2)*

- **User Value:** ★★★★★ — removes the single most universally-felt confusion; runs
  become rememberable and discussable for all five personas.
- **Recruiter Demo Value:** ★★★★★ — instantly transforms every screen from "DB dump"
  to "product." The cheapest possible credibility win.
- **Engineering Effort:** **M** — one read-side join helper on `DashboardData`; the
  cost is touching all four pages' tables/pickers/axes consistently.
- **Technical Risk:** **Med** — display-only, but `run_uuid` is the key behind every
  selector; the label must stay strictly cosmetic (label↔uuid map) or selection breaks.
  Guard with tests on the helper.
- **Dependencies:** none (it is a dependency *for* R5/R6). Build E1 (verdict styling)
  alongside if convenient.
- **Why first:** Highest payoff-to-risk ratio, unblocks comparison items, and every
  later screenshot benefits.

### R2 — Failure Explanations  *(gap item 3)*

- **User Value:** ★★★★★ — fulfills the platform's core promise; turns `passed=False`
  from a dead end into "here's the model's wrong answer and why it's wrong."
- **Recruiter Demo Value:** ★★★★★ — "it shows the model's actual vs expected output" is
  the strongest single demo moment available.
- **Engineering Effort:** **S–M** — pure presentation of data `run_detail()` already
  returns (`actual` / `expected` / `input` / scorer `detail`).
- **Technical Risk:** **Low** — display-only, no schema, no new query.
- **Dependencies:** none. **Produces the shared per-case detail component** reused by
  R4, R7 (explorer), R8 (root cause), R9 (perfect-run).
- **Why second:** Lowest risk of the ★★★★★ items, and it builds the component four
  later items reuse — a force multiplier.

### R3 — Feature Overview Panel  *(gap item 1)*

- **User Value:** ★★★★☆ — finally says *what is being tested* and *is the system
  healthy right now*; serves PM/recruiter/first-time directly.
- **Recruiter Demo Value:** ★★★★☆ — the landing screen tells a product story + a
  headline outcome ("caught N regressions") instead of "Features under test: 1."
- **Engineering Effort:** **S–M** — mostly authored copy (`help_text.py`) + one stats
  read helper + a Home layout block.
- **Technical Risk:** **Low** — additive, read-only; verdict reuses active-baseline read.
- **Dependencies:** E1 (verdict styling) for the health signal; benefits from R1's
  labels in the "latest run" line.
- **Why third:** It's the *first* thing a demo viewer sees; once R1/R2 make the inner
  pages credible, the front door should match.

### R4 — Pass Explanations  *(gap item 4)*

- **User Value:** ★★★☆☆ — teaches what "good" looks like; reassurance and symmetry.
- **Recruiter Demo Value:** ★★★☆☆ — completes the "every case is explained" story.
- **Engineering Effort:** **S** — effectively free: same component as R2, also enabled
  for passing cases (collapsed by default).
- **Technical Risk:** **Low** — display-only, shares R2's data path.
- **Dependencies:** **R2** (same component).
- **Why in P0:** It costs almost nothing once R2 exists and closes the explainability
  loop, so it rides along at the end of the P0 block rather than being deferred.

**P0 exit state:** named runs everywhere, every failure (and pass) explained in words,
a product-framed home page with a health verdict. This is the minimum bar for a
recruiter demo.

---

## P1 — High value (the "this is a real evaluation tool" layer)

> Goal of P1: depth and interactivity — comparison, drill-down, and browseable
> evidence. These turn a clear dashboard into a credible *evaluation platform*.

### R5 — Run Comparison (A vs B)  *(gap item 5)*

- **User Value:** ★★★★☆ — answers the AI-engineer's real question ("my new prompt vs
  the old one") that the baseline-only Regressions page can't.
- **Recruiter Demo Value:** ★★★★★ — "pick any two runs and diff them" is a marquee demo.
- **Engineering Effort:** **M** — reconstruct two runs + a side-by-side/delta table;
  **reuses `RegressionDetector.compare` and `flatten_metrics` — no new math.**
- **Technical Risk:** **Med** — two reconstructions are cheap; keep it to *two*, and
  thread selection state cleanly (E2/R1 labels in the pickers).
- **Dependencies:** **R1** (readable labels in the two pickers); shares delta rendering
  with R6.
- **Why first in P1:** Highest demo value in the tier; the comparison surface is the
  host for R6.

### R6 — Delta Analysis  *(gap item 6)*

- **User Value:** ★★★★☆ — converts "a number moved" into "metric X went 0.91→0.86
  (−5%), and the prompt changed."
- **Recruiter Demo Value:** ★★★★☆ — quantified, attributed deltas read as rigor.
- **Engineering Effort:** **S–M** — present `MetricComparison` fields the detector
  already returns (`delta`, `relative_delta`, `reason`, `prompt_changed`/
  `dataset_changed`).
- **Technical Risk:** **Low–Med** — derive-only; Med only if also fused onto Trends.
- **Dependencies:** **R5** (lives inside the comparison view); reuses E1 verdicts.
- **Why here:** It's the explanatory half of R5 — build them as a pair, R5 then R6.

### R7 — Full Test Log Explorer  *(gap item 8)*

- **User Value:** ★★★★☆ — lets any viewer browse the evidence: filter to failures,
  search, sort, expand.
- **Recruiter Demo Value:** ★★★★☆ — "every example, searchable" demonstrates depth.
- **Engineering Effort:** **M** — UI-heavy (filters/sort), data already reconstructed.
- **Technical Risk:** **Low** — display-only over one run's existing data.
- **Dependencies:** **R2** (reuses the per-case detail expander); reads better with R1.
- **Why here:** Turns R2's single-case view into a full exploration surface; natural
  follow-on.

### R8 — Root Cause Analysis  *(gap item 10)*

- **User Value:** ★★★★★ — closes the loop from "metric regressed" to "these exact
  cases," with the discarded plain-English reason restored.
- **Recruiter Demo Value:** ★★★★★ — "click the red metric → see the failing emails" is
  the most complete narrative arc in the product.
- **Engineering Effort:** **M–L** — the reason text is easy; the **metric→cases mapping**
  (esp. segment/scorer metrics) is the real, test-worthy work.
- **Technical Risk:** **Med** — derive-only (no schema), but the attribution logic is
  new and must be correct; it belongs in a pure `DashboardData` helper with unit tests.
- **Dependencies:** **R2** (case detail), **R6** (reason/delta rendering), R1 (labels).
- **Why last in P1:** Highest value in the tier but depends on the most prior pieces;
  sequencing it after R2/R6/R7 means the components it needs already exist.

**P1 exit state:** arbitrary run comparison with attributed deltas, a searchable case
explorer, and regressions that explain themselves *and* point to the offending cases.
This is a portfolio-grade evaluation tool.

---

## P2 — Nice to have (polish and guidance)

### R9 — Dataset Explorer  *(gap item 9)*

- **User Value:** ★★★★☆ — answers "what is the model tested on?"; the hand-labeled
  golden set is a credibility asset.
- **Recruiter Demo Value:** ★★★★☆ — strong, but the dataset isn't the *headline* story.
- **Engineering Effort:** **M** — new view reusing `DatasetRegistry`; decide source
  (on-disk JSON is richer — includes `notes`/`description`).
- **Technical Risk:** **Low** — read-only; minor: reads outside the SQLite path.
- **Dependencies:** none hard (independent); reads nicely after R7's filter patterns.
- **Why P2:** High value but standalone and non-blocking; it can slot in any time and
  is demarcated from the core regression narrative.

### R10 — KPI Drilldowns  *(gap item 7)*

- **User Value:** ★★★★☆ — every KPI gains a definition, units, a verdict, and a path to
  its underlying cases.
- **Recruiter Demo Value:** ★★★☆☆ — supports the "everything is explained" narrative
  more than it creates its own moment.
- **Engineering Effort:** **M** — spread across several tiles/tables; copy + baseline-
  delta verdict wiring.
- **Technical Risk:** **Low** — additive display; verdict reuses active-baseline read.
- **Dependencies:** E1 (verdicts), and R8's metric→cases mapping for the "drill to
  cases" links.
- **Why P2:** Much of its value is delivered incrementally by E1 + R3 + R8 already;
  the remaining polish (per-tile `help=`, links) is a finishing pass, best done once
  the drill targets (R8) exist.

### R11 — Perfect Run Recommendations  *(gap item 11)*

- **User Value:** ★★★☆☆ — frames "what would make this green"; pleasant guidance.
- **Recruiter Demo Value:** ★★★☆☆ — the least essential of the set.
- **Engineering Effort:** **M–L** — summarization logic + careful plain-language framing.
- **Technical Risk:** **Med** — derive-only, but interpretive; wording must not
  over-promise ("guaranteed perfect"), and the gap math needs tests.
- **Dependencies:** **R2** (failing cases), **R8** (metric→cases + thresholds/baseline
  distance).
- **Why last:** Lowest essential value, highest framing risk, most dependencies. Ship it
  only after everything it builds on is solid.

**P2 exit state:** the dataset is browsable, every KPI is self-explaining with
drill-downs, and runs offer guidance toward a perfect result. Complete platform.

---

## Recommended implementation order

A single linear sequence, dependency-correct, front-loading comprehension and demo
payoff. Each step is independently shippable and leaves the system green.

| Step | Item | Tier | Builds / unlocks | Effort |
|:----:|------|:----:|------------------|:------:|
| 1 | **R1** Human-Readable Run Names (+ E1 verdict helper) | P0 | every page; unlocks R5/R6 | M |
| 2 | **R2** Failure Explanations | P0 | shared case-detail component (R4/R7/R8/R9/R11) | S–M |
| 3 | **R3** Feature Overview Panel | P0 | the demo front door | S–M |
| 4 | **R4** Pass Explanations | P0 | rides on R2 | S |
| 5 | **R5** Run Comparison (A vs B) | P1 | host surface for R6 | M |
| 6 | **R6** Delta Analysis | P1 | explanatory half of R5 | S–M |
| 7 | **R7** Full Test Log Explorer | P1 | reuses R2 component | M |
| 8 | **R8** Root Cause Analysis | P1 | reuses R2 + R6; unlocks R10/R11 | M–L |
| 9 | **R9** Dataset Explorer | P2 | independent | M |
| 10 | **R10** KPI Drilldowns | P1→polish | reuses E1 + R8 | M |
| 11 | **R11** Perfect Run Recommendations | P2 | reuses R2 + R8 | M–L |

### Rationale for the ordering

- **Steps 1–4 (all P0) come first** because they make the dashboard demo-credible: a
  viewer can read every screen, see a verdict, and understand any failure. This is the
  minimum a recruiter should see.
- **R1 leads** despite being Med-risk because it's the highest payoff-to-effort win and
  it unblocks the comparison items; **R2 follows** as the lowest-risk ★★★★★ item that
  *also* yields the component four later items reuse.
- **R5→R6 then R7→R8** is the P1 spine: build the comparison surface, add its delta
  explanation, broaden into the case explorer, then land the root-cause drill that
  depends on all three.
- **R9/R10/R11 close out** as polish and guidance: independent (R9), a finishing pass
  best done after its drill targets exist (R10), and the dependency-heaviest,
  highest-framing-risk item (R11) genuinely last.

### Demo milestones (for recruiter readiness)

- **After Step 4 (P0 done):** a clean, named, self-explaining dashboard where every
  failure shows the model's wrong answer. *This is already demoable.*
- **After Step 8 (P1 done):** add "diff any two runs" and "click a regression → see the
  exact failing emails." *This is the strong, full-story demo.*
- **After Step 11 (P2 done):** browseable golden dataset, self-explaining KPIs, and
  perfect-run guidance. *This is the complete, polished platform.*

### Phase 5 working agreement (carryover)

Per the original brief and CLAUDE.md: implement **one item at a time**; for each —
state the goal and why it matters, list files that will change, name the risks,
implement, run Ruff + pytest, verify existing functionality (and demo mode) still work,
summarize results, and **wait for approval before the next item.** New read logic lands
in `DashboardData` with tests; explanatory copy lands in `help_text.py`; no schema
changes are anticipated for any item.
