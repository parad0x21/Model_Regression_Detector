"""Plain-English help content for the dashboard pages.

Kept Streamlit-free so the copy lives in one place and can be imported/linted
without the Streamlit dependency. Rendered by ``_shared.render_page_help``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageHelp:
    """Help shown for one page: a main-column caption plus sidebar reference."""

    caption: str = ""
    overview: str = ""  # short framing, shown as an info box in the sidebar
    sections: tuple[tuple[str, str], ...] = ()  # (expander title, markdown body)


_RUNS_GLOSSARY = (
    "- **Pass rate** — share of cases the feature got *completely* right. "
    "90%+ is strong; a sudden drop is the thing to worry about.\n"
    "- **Passed / Failed / Errored** — fully correct · wrong on a check · "
    "crashed (e.g. the model returned invalid output).\n"
    "- **Scorer mean_score** — each scorer grades one aspect (`category_match` = "
    "right category, `summary_quality` = sensible summary). 1.0 = perfect.\n"
    "- **Segment metrics** — the same scores split by group (here, email "
    "category), so you can see which categories are strong or weak.\n"
    "- **Per-case results** — raw detail per example: pass/fail, **latency** "
    "(time), and **tokens** (a proxy for cost)."
)

_TRENDS_GLOSSARY = (
    "- **Pass rate** — higher is better; a downward step warns a change hurt quality.\n"
    "- **Scorer means** — per-aspect quality; one scorer dropping pinpoints *what* got worse.\n"
    "- **Latency (ms)** — time per case; lower is better. **p95** is the slow tail "
    "(95% of cases are faster than this).\n"
    "- **Token usage** — a stand-in for cost; lower is better. A jump means pricier runs."
)

_REGRESSIONS_GLOSSARY = (
    "- 🟡 **WARNING** — a noticeable dip worth reviewing, but not release-blocking.\n"
    "- 🔴 **CRITICAL** — a drop big enough that shipping is risky. In CI this fails the "
    "build and **blocks the merge**, exactly like a failing test.\n"
    "- **delta** — how much the metric changed vs the baseline; the detector has "
    "already decided this move is bad.\n"
    "- **No regressions** = the run held up against the baseline. That's the good outcome."
)

_BASELINES_GLOSSARY = (
    "- Without a fixed reference, a 6% drop looks like a normal day — a baseline gives "
    "an objective 'better or worse than what we trust?' line.\n"
    "- Baselines are promoted **deliberately** (or automatically when `main` is green), "
    "so a worse run never silently becomes the new bar.\n"
    "- **Promotion history** shows every time the bar moved, and who or what moved it."
)

_HOME_PAGES = (
    "- **Runs** — every evaluation of the feature, with its scores. Inspect one run.\n"
    "- **Trends** — how scores, speed, and cost move across runs over time.\n"
    "- **Regressions** — where a run got worse than the baseline, and how serious.\n"
    "- **Baselines** — the current 'known-good' run everything is compared to."
)

_HOME_TERMS = (
    "- **Run** — one evaluation of the feature against the test set.\n"
    "- **Pass rate** — share of cases the feature got fully right. Higher is better.\n"
    "- **Baseline** — the trusted 'known-good' run new runs are measured against.\n"
    "- **Regression** — a new run doing measurably worse than the baseline.\n"
    "- **Severity** — WARNING (worth a look) vs CRITICAL (blocks a release)."
)


PAGE_HELP: dict[str, PageHelp] = {
    "home": PageHelp(
        sections=(
            ("The four pages", _HOME_PAGES),
            ("Key terms, in plain English", _HOME_TERMS),
        ),
    ),
    "runs": PageHelp(
        caption="Each row is one evaluation of the feature — open one to see how it scored.",
        overview=(
            "**What am I looking at?** A *run* is a single test of the AI feature against a "
            "fixed set of hand-labeled examples. Pick a run to see its scores and every result."
        ),
        sections=(("What the metrics mean", _RUNS_GLOSSARY),),
    ),
    "trends": PageHelp(
        caption="Each point is one run, oldest to newest.",
        overview=(
            "**What am I looking at?** Trends show whether the feature is improving, holding "
            "steady, or sliding over time. Each line tracks one metric across past runs."
        ),
        sections=(("How to read these charts", _TRENDS_GLOSSARY),),
    ),
    "regressions": PageHelp(
        caption="Where a run scored worse than the trusted baseline.",
        overview=(
            "**What is a regression?** When a new run scores measurably worse than the "
            "baseline, MRDS flags each metric that moved the wrong way and rates its severity."
        ),
        sections=(("Severity, and why deployments get blocked", _REGRESSIONS_GLOSSARY),),
    ),
    "baselines": PageHelp(
        caption="The trusted 'known-good' run that every new run is compared against.",
        overview=(
            "**What is a baseline?** One run, marked as the trusted bar for quality. Exactly "
            "one baseline is active per feature, and every new run is measured against it."
        ),
        sections=(("Why comparisons use a baseline", _BASELINES_GLOSSARY),),
    ),
}
