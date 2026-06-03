# Product & UX Audit (Phase 2)

> **Status:** UX/product evaluation only. No code was read for *how* to fix things,
> and **no solutions are proposed here** — Phase 3 (gap analysis) and Phase 4
> (roadmap) come next. This document judges the product purely on **understanding
> and communication**: what a viewer with *no prior knowledge of MRDS* sees,
> understands, misreads, or is left wondering about.
> **Source of truth:** [current-system-analysis.md](current-system-analysis.md).
> **Date:** 2026-06-02.

A single lens runs through everything below:

> **The recurring failure is not missing data — it is unexplained data.**
> The dashboard frequently shows a number, a table, or a chart and trusts the
> viewer to already know what it means, whether it is good or bad, and what caused
> it. Phase 1 proved the *meaning* is usually computable or already stored; Phase 2
> shows where the *communication* of that meaning is absent.

---

## Part A — Audit by Perspective

Five viewers, each arriving cold. For each: what lands immediately, what confuses,
what questions go unanswered, what would build trust, and what would speed comprehension.

### 1. Recruiter

*Goal: in ~60 seconds, decide "is this person's work impressive and real?"*

- **Immediately understands:** This is a serious, multi-page engineering project with
  a polished, professional surface. The home page's "safety net for AI features"
  analogy is genuinely strong — a non-technical recruiter grasps the *pitch* fast.
  The four-page structure signals breadth.
- **Confusing:** The moment they click into Runs, they hit a wall of 32-character
  hexadecimal IDs and column names like `p95_latency_ms` and `mean_score`. It looks
  like a database admin tool, not a product. They cannot tell a "good" run from a
  "bad" one at a glance.
- **Unanswered questions:** *"What did this person actually build? Is it impressive?
  What's the headline result?"* There is no single screen that says "this system
  caught N regressions" or "here is a real one it blocked." The story is present in
  the data but never told.
- **Would build trust:** A visible, plain-language "win" — a concrete example of a
  bad change being caught and blocked — and human-readable run identities so the
  screens look like a product, not a dump.
- **Would speed comprehension:** A headline status ("currently healthy / blocked")
  and named runs on the very first interactive screen.

### 2. Engineering Manager

*Goal: "would this catch a quality regression before it shipped, and can my team operate it?"*

- **Immediately understands:** The CI-gating concept (severity → blocked merge) is
  exactly the mental model they have for tests, and the Regressions page speaks their
  language. Baselines-as-a-promotion-bar maps cleanly to "known good."
- **Confusing:** Severity thresholds are asserted but not justified on screen — *why*
  is this a CRITICAL and that a WARNING? The Regressions page shows the regressed
  metrics but not the metrics that held, so they can't judge the *overall* health of
  a candidate, only its worst spots.
- **Unanswered questions:** *"What baseline was this compared against, and was that a
  fair comparison (same dataset)? Who promoted the current bar, and was it a good
  one? If I saw a red run, what would I tell an engineer to go fix?"*
- **Would build trust:** Seeing the regression explained in words (not just a delta),
  and being able to trace a regressed metric down to the specific failing cases.
- **Would speed comprehension:** A run header that states, up front, "compared to
  baseline X, on dataset vN, prompt vM" so the comparison's validity is self-evident.

### 3. Product Manager

*Goal: "what does this feature do for customers, and is its quality trending the right way?"*

- **Immediately understands:** Trends communicate direction (up/down) intuitively;
  "pass rate" is self-explanatory as a quality proxy.
- **Confusing:** What is actually being measured? The feature under test
  (email classification into billing/technical/account/general) is **never described
  in business terms** anywhere in the UI. "Scorer means" and "segment metrics" are
  engineering vocabulary; a PM doesn't know `category_match` is "did we route the
  email to the right team."
- **Unanswered questions:** *"Which customer-facing capability is this? Which
  categories are we weak on, and does that matter to the business? Why did the line
  move on this date — a prompt change, a model change, a harder dataset?"* Trends show
  *that* something moved but never *why*.
- **Would build trust:** Business-framed labels (what each category/scorer means for a
  customer) and the ability to attribute a trend movement to a cause (a prompt or
  model change).
- **Would speed comprehension:** One sentence of context per feature, and per-category
  performance phrased as "we're strong at billing, weak at account."

### 4. AI Engineer

*Goal: "I changed a prompt/model — did it regress, where exactly, and on which examples?"*

- **Immediately understands:** The evaluation model (golden dataset → scorers →
  aggregate metrics → baseline comparison) is familiar and well-built. Latency/token
  tracking and per-segment breakdowns are exactly what they'd want.
- **Confusing:** The per-case table tells them *which* cases failed but strips out the
  two things they most need: **the model's actual output** and **the expected
  output**. They can see `passed = False` but not the wrong answer — even though
  Phase 1 confirms both are stored. This is the single most frustrating gap for this
  persona.
- **Unanswered questions:** *"On a failing case, what did the model say vs. what we
  wanted? Which scorer failed and why? Can I compare two specific runs (my new prompt
  vs the old one) directly, not just against the baseline? What would a perfect run
  require?"*
- **Would build trust:** Surfacing `actual` vs `expected` and the per-scorer `detail`
  string ("expected 'billing', got 'technical'") — proof the system actually
  inspects outputs, not just counts.
- **Would speed comprehension:** Failure-first views (filter to failures) and an
  arbitrary run-A-vs-run-B comparison, since that's their real workflow.

### 5. First-Time User

*Goal: "what is this and what am I looking at?"*

- **Immediately understands:** The home page does its job — the analogy and sidebar
  guide give a real fighting chance. They know it's about catching AI quality drops.
- **Confusing:** Everything past Home assumes vocabulary the home page didn't fully
  teach: UUIDs, "candidate," "segment," "p95," "scorer." The help text lives in the
  sidebar and is easy to miss while staring at a table. Each page restarts the
  feature picker with no memory of the last choice, which feels disjointed.
- **Unanswered questions:** *"Which of these numbers should I care about? Is what I'm
  seeing good? What do I do next?"* There is no notion of a guided path or a "you are
  here / this is fine."
- **Would build trust:** Consistent plain-language labeling on the data itself (not
  only in the sidebar), and an at-a-glance good/bad signal on every screen.
- **Would speed comprehension:** Naming runs like a human would, and color/word cues
  (good/warning/critical) attached directly to the numbers.

### Cross-perspective synthesis

| Theme | Recruiter | EM | PM | AI Eng | First-time |
|------|:--:|:--:|:--:|:--:|:--:|
| Opaque UUID run identity hurts | ●●● | ●● | ● | ●● | ●●● |
| No "is this good/bad?" verdict on data | ●●● | ●● | ●● | ● | ●●● |
| Feature has no business description | ●● | ● | ●●● | ● | ●● |
| Failures shown but not *explained* | ● | ●● | ● | ●●● | ●● |
| Regression numbers without words/cause | ● | ●●● | ●● | ●● | ● |
| No run-to-run (A vs B) comparison | – | ●● | ● | ●●● | – |
| No "why did the trend move?" attribution | – | ● | ●●● | ●● | ● |

The two universally-felt problems: **opaque run identity** and **data shown without a
verdict**. They affect every viewer on every page.

---

## Part B — Page-by-Page Audit

Each page is judged against the criteria in the brief, then summarized in the required
nine sections.

---

### HOME

**Clarity / Onboarding / First impression / Business context / Trust**

- **Does a user understand what MRDS does within 30 seconds?** *Mostly yes.* The
  "safety net… just like unit tests and CI" framing is the strongest piece of
  communication in the whole product. A newcomer leaves Home knowing the *purpose*.
- **Does a user understand what feature is being evaluated?** *No.* Home shows
  "email_classifier — N runs" as a bare identifier. It never says what that feature
  does, who uses it, or what the four categories are. The thing under test is invisible
  as a *product*.
- **Does a user understand why the platform matters?** *Yes, conceptually* — the
  blocking-deployments analogy lands. But the "why it matters" is told in the
  abstract; it's never made concrete with a real example of a catch.

#### What Works
- The safety-net analogy is clear, memorable, and non-technical.
- The sidebar page-guide and key-terms glossary are genuinely helpful framing.
- Listing features with run counts gives an honest sense of scope.

#### What Confuses Users
- "Features under test: 1" reads as an oddly small, anticlimactic headline metric.
- `email_classifier` is shown as a raw slug, not a described capability.
- The page tells you the system *can* block deployments but shows no evidence it ever
  has — the claim and the proof are disconnected.

#### Missing Information
- A one-line business description of the feature under test and its categories.
- A current health verdict (is everything green right now, or is something blocked?).
- A concrete headline outcome ("caught N regressions across M runs").

#### Highest-Impact Improvements *(framed as gaps, not solutions)*
- The feature needs a human description, not just a slug.
- The landing screen needs a verdict/outcome, not just a count.

#### Recruiter Impression
Strong first 10 seconds (great pitch), but no "wow" payoff — nothing says *"look what
this caught."* Leaves impressed by the framing, unsure of the substance.

#### Engineering Manager Impression
Recognizes the value proposition instantly and trusts the framing. Wants the home page
to surface operational status (healthy/blocked) rather than a feature count.

#### Product Manager Impression
Frustrated that the actual customer-facing capability is reduced to an engineering
slug. The "why it matters" is generic, not tied to this product.

#### AI Engineer Impression
Skims Home as marketing copy and heads straight for Runs/Trends; Home isn't aimed at
them, which is fine — but it under-sells the rigor underneath.

#### First-Time User Impression
The best-served persona here. Leaves Home genuinely oriented — then loses the thread
immediately on the next page.

---

### RUNS

**Run discoverability / Readability / Explainability / Information hierarchy**

- **Does the user understand what a run represents?** *Weakly.* The sidebar says "a
  single test of the feature against hand-labeled examples," but the table itself —
  led by a UUID — doesn't reinforce it. Nothing on the row says "this is the 12th
  evaluation, on this date, of this model."
- **Can they determine whether a run was good or bad?** *Only after work.* The pass
  rate is present once you select a run, but there's no good/bad coloring, no
  comparison to baseline on this page, and no verdict. A 0.83 pass rate is shown
  identically whether it's a triumph or a disaster.
- **Can they understand why tests passed or failed?** *No — and this is the headline
  finding.* The per-case table shows `passed = False` but **withholds the actual
  output, the expected output, and the per-scorer reason**, all of which are stored.
  The user sees *that* something failed and is given no way to see *why*.
- **Can they identify the most important information quickly?** *No.* Everything is
  presented at one flat visual weight — the UUID column gets the same emphasis as the
  pass rate. There's no hierarchy guiding the eye to the verdict.

#### What Works
- The drill-down is genuinely rich: KPI tiles, scorer table, segment-by-category
  table, and per-case detail are all the *right* facets.
- Segment metrics already expose per-category strength/weakness — a real insight,
  if the viewer knows to read it.
- The prompt/dataset/model/duration caption captures reproducibility context.

#### What Confuses Users
- The opaque 32-char UUID as both the table's lead column and the run picker — viewers
  can't tell runs apart or remember which they selected.
- Column names are raw field names (`mean_score`, `latency_ms`, `total_tokens`) with
  no units explained in-context.
- `passed = False` with no adjacent explanation reads as a dead end.
- No way to filter to failures, so on a 54-case run the user hunts manually.

#### Missing Information
- The model's **actual answer vs the expected answer** on each case (stored, unshown).
- The per-scorer **`detail`** explanation per case (stored, unshown).
- A good/bad verdict and a comparison to the baseline *for this run*.
- A human-readable run identity (date, model, dataset version, sequence number).

#### Highest-Impact Improvements *(gaps, not solutions)*
- Failures must become *explainable* on this page — the why is the missing core.
- Run identity must become human-readable while preserving the internal id.

#### Recruiter Impression
This is where the polished first impression breaks. It looks like raw database output.
A recruiter scrolling here sees complexity but no clarity.

#### Engineering Manager Impression
Appreciates the depth but wants a verdict and a baseline comparison on the run itself,
plus the ability to drill from a weak segment into the actual failing cases.

#### Product Manager Impression
Lost in field-name vocabulary. Can see *that* "account" is the weak category (if they
decode the segment table) but gets no business interpretation of what that costs.

#### AI Engineer Impression
The most under-served-relative-to-need persona. The exact diagnostic data they live
on (actual vs expected, scorer reasons) is collected and then hidden one layer down.
Deeply frustrating — so close, yet unusable for debugging.

#### First-Time User Impression
Overwhelmed. Goes from "I get it" on Home to "what am I looking at?" within one click.
The UUIDs and unit-less columns are the trigger.

---

### TRENDS

**Trend clarity / Interpretation difficulty / Business usefulness**

- **Does the user understand what changed?** *Direction, yes; substance, no.* They see
  a line step down but the x-axis is truncated UUIDs, so they can't tell *which* run
  or *when*. "Something got worse around here" is the ceiling of comprehension.
- **Does the user understand why metrics moved?** *No.* Nothing annotates a step with
  its cause (prompt change, model change, harder dataset). The dashboard has the
  version info to attribute movement but the trend never connects the two.
- **Can the user identify regressions?** *Only by eye.* A drop is visible but not
  *marked* — there's no indication of which point crossed a warning/critical
  threshold, nor which point is the baseline. The official regression verdict lives on
  a different page, disconnected from the visual.

#### What Works
- Four clean, separate charts for the right metric families (quality, scorer detail,
  latency, cost) — the conceptual coverage is correct.
- Splitting scorer means out lets a viewer see *which aspect* of quality moved.
- Efficient and uncluttered; not over-decorated.

#### What Confuses Users
- Truncated-UUID x-axis labels are meaningless as time/identity markers.
- No baseline line, no regression markers — the charts and the system's own verdicts
  are visually divorced.
- "Token usage" as a cost proxy isn't framed as cost; a PM won't read it that way.

#### Missing Information
- Time/readable identity on the x-axis so movement can be placed and discussed.
- Cause annotation for steps (what changed between adjacent runs).
- Visual marking of the baseline and of runs that regressed.

#### Highest-Impact Improvements *(gaps, not solutions)*
- Movements need *attribution* ("why did it move") to be useful, not just visible.
- Regression/baseline context needs to live *on* the trend, where the eye already is.

#### Recruiter Impression
Charts look professional and "data-sciencey," which photographs well — but a recruiter
can't extract a story from them.

#### Engineering Manager Impression
Wants the trend to mark where the bar (baseline) sits and where the line breached a
threshold — i.e. to fuse the Trends and Regressions stories.

#### Product Manager Impression
This is the page closest to a PM's needs, and the biggest near-miss: it shows
direction but never *why*, so it can't drive a decision or a narrative.

#### AI Engineer Impression
Useful as a sanity check, but they'll want to click a suspicious point to jump to that
run's failures — and can't. The chart is a dead-end observation, not a launchpad.

#### First-Time User Impression
Understands "up good, down bad" and little else. The unreadable x-axis prevents them
from anchoring what they're seeing to anything real.

---

### REGRESSIONS

**Actionability / Clarity / Root-cause visibility**

- **Does the page explain regressions?** *Numerically, not verbally.* It shows
  metric/baseline/candidate/delta/severity. The detector actually *computes a
  plain-English reason* for each, but that reason is dropped before it reaches this
  page — so the explanation exists and is then thrown away.
- **Does the user know what to fix?** *No.* A regressed metric (e.g.
  `scorer.category_match.mean_score` fell) is never linked to the specific cases that
  dragged it down. The user is told the *symptom* with no path to the *cause*.
- **Does the page explain impact?** *Partially.* Severity implies impact (CRITICAL
  blocks a merge), but the page doesn't say "this would have blocked your deploy," nor
  how many cases/categories are affected, nor against which baseline.

#### What Works
- Severity maps directly to the CI gate — the one concept EMs trust instantly.
- The empty/clean state ("No regressions recorded") is a clear, reassuring success
  signal.
- Showing baseline vs candidate values side by side is the right comparison shape.

#### What Confuses Users
- Metric names are raw flattened paths (`segment.account.category_match`) — opaque to
  anyone but the author.
- Only *regressed* metrics appear, so the viewer can't see the full picture (what held
  up), making the run feel worse than it may be.
- No words explaining *why* each delta is bad, despite that text being computed.
- The baseline being compared against is identified only by an internal id, if at all.

#### Missing Information
- The human-readable **reason** per regression (computed, then discarded).
- A link/path from a regressed metric to the **failing cases** behind it.
- The full comparison (passed metrics too), and a clear "this blocks/doesn't block."
- A readable identity for both the candidate and its baseline.

#### Highest-Impact Improvements *(gaps, not solutions)*
- Regressions must be explained in words and connected to their root-cause cases.
- The page must state impact plainly ("this would block the deploy").

#### Recruiter Impression
Conceptually the most impressive page (this is the product's whole point), but it
reads as a bare numeric table — the impressiveness is buried.

#### Engineering Manager Impression
The closest page to their mental model, yet it stops exactly where they need it to
continue: it flags the regression but offers no route to the cause or the fix.

#### Product Manager Impression
Understands "red = bad" but can't translate a regressed flattened-metric name into a
customer-impact statement.

#### AI Engineer Impression
Wants to click a regressed metric and land on the failing cases. The absence of that
drill-path makes this a notification, not a debugging tool.

#### First-Time User Impression
Sees a small table of numbers and a severity word. Without knowing the metrics, they
take "severity: critical" on faith and move on, learning little.

---

### BASELINES

**Trustworthiness / Understandability / Decision support**

- **Does the user understand what a baseline is?** *Yes, in principle.* The sidebar
  framing ("the trusted known-good bar") is clear, and the active-baseline + history
  layout reinforces it.
- **Does the user understand why it matters?** *Yes.* The "without a fixed reference, a
  6% drop looks like a normal day" copy is excellent and earns trust in the concept.
- **Does the user understand how current runs compare?** *No.* The page shows *which*
  run is the baseline but not *what quality it represents* (no metrics), and offers no
  way to see how the latest run stacks up against it. It establishes the bar's
  existence but not its height.

#### What Works
- The promotion-history audit trail (who promoted, when, note) is trust-building and
  professional.
- The "why a baseline exists" explanation is one of the clearest pieces of copy in the
  app.
- The single-active-baseline rule is communicated clearly.

#### What Confuses Users
- The baseline is identified by raw UUID, so it's an abstract pointer, not a thing you
  can picture.
- No metrics are shown for the baseline run — the viewer can't see the actual quality
  level the bar enforces without leaving for the Runs page.
- "Promoted by demo / manual" is shown without context for what promotion *did*.

#### Missing Information
- The baseline run's headline metrics (the height of the bar).
- A direct comparison of the current/latest run against the baseline.
- A readable identity for the baseline run.

#### Highest-Impact Improvements *(gaps, not solutions)*
- The baseline needs to show *what quality it represents*, not just *which run it is*.
- The page should support the actual decision ("is my latest run above or below the bar?").

#### Recruiter Impression
Looks orderly and governed (an audit trail reads as maturity), but abstract — there's
no concrete sense of what "the bar" actually is.

#### Engineering Manager Impression
Values the governance/audit story highly. Wants to see the baseline's metrics and a
one-glance "current vs bar" to support promotion decisions.

#### Product Manager Impression
Understands the concept but can't connect it to product quality without numbers
attached to the bar.

#### AI Engineer Impression
Wants the baseline to be a launchpad: see its metrics, and compare their candidate
against it directly from here.

#### First-Time User Impression
Arguably the second-best-explained page after Home — the *concept* lands. The
abstraction (UUID, no metrics) is what stops it short of fully satisfying.

---

## Part C — Catalogue: Data Shown Without Meaning

Per the brief, every place the dashboard **displays data but fails to explain its
meaning, verdict, or cause**. This is the consolidated communication-gap list.

| # | Where | Data shown | Meaning that is *not* communicated |
|---|-------|-----------|-------------------------------------|
| 1 | Home | `email_classifier` | What the feature does; what its categories mean in business terms. |
| 2 | Home | "Features under test: 1" | Whether the system is currently healthy or blocked; what it has caught. |
| 3 | Runs (list) | 32-char UUID | Which run this is, when, on what model/dataset. |
| 4 | Runs (KPIs) | Pass rate e.g. 0.83 | Whether that's good or bad; how it compares to the baseline. |
| 5 | Runs (per-case) | `passed = False` | **Why** it failed — the actual vs expected answer (stored, hidden). |
| 6 | Runs (per-case) | (no scorer detail column) | The per-scorer `detail` reason (stored in `scores_json`, hidden). |
| 7 | Runs (columns) | `mean_score`, `p95_latency_ms` | Units and plain-language meaning, in-context (not just sidebar). |
| 8 | Runs (segments) | per-category pass rates | Which categories are strong/weak *and why that matters*. |
| 9 | Trends (x-axis) | truncated UUIDs | When each run happened; readable identity. |
| 10 | Trends (steps) | a line moving up/down | **Why** it moved (prompt/model/dataset change). |
| 11 | Trends | the lines themselves | Where the baseline sits; which points regressed. |
| 12 | Regressions | metric/delta/severity rows | The plain-English **reason** (computed, then discarded). |
| 13 | Regressions | a regressed metric name | Which **cases** caused it (no root-cause link). |
| 14 | Regressions | (regressed rows only) | What *held up*; whether this blocks the deploy. |
| 15 | Regressions | `segment.account.category_match` | A readable name a non-author can parse. |
| 16 | Baselines | baseline run UUID | The baseline's **metrics** — the height of the bar. |
| 17 | Baselines | active baseline | How the **current/latest run compares** to it. |
| 18 | All pages | severity / pass-fail values | A consistent good/warning/critical visual verdict on the data itself. |

**The pattern is unmistakable:** in the large majority of these, the meaning is
**already computed or already stored** (Phase 1, §6) — the dashboard simply stops at
the number and never states what it means, whether it's good, or what caused it.

---

## Part D — Top Findings (understanding-first, no solutions)

In priority order of *comprehension impact* across all personas and pages:

1. **Run identity is opaque.** UUIDs on every list, picker, and axis make runs
   un-rememberable and un-discussable. Felt by all five personas. *(Display-only fix
   required; internal id must be preserved.)*
2. **Failures are shown but never explained.** The single richest debugging data
   (actual vs expected, scorer reasons) is collected and hidden — the platform's core
   promise (explainability) is unmet at the exact moment it matters.
3. **Data carries no verdict.** Numbers appear without "is this good/bad?" coloring,
   baseline comparison, or threshold context, so viewers can't interpret what they see.
4. **Regressions lack words and root cause.** A computed plain-English reason is
   discarded, and no path connects a regressed metric to the cases behind it.
5. **The feature has no business context.** Nowhere does the UI say what the email
   classifier *does* for customers, so PMs and recruiters can't connect metrics to value.
6. **Trends show movement without cause.** Direction is visible; attribution
   (what changed) and regression/baseline context are absent.
7. **Baselines establish a bar without its height.** The trusted reference is named
   but its quality level and a current-vs-bar comparison are missing.

These seven findings — all about *communication*, not capability — define the input to
Phase 3's gap analysis. No implementation is implied here; Phase 3 will size each gap
against the data Phase 1 already located.
