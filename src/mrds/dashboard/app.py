"""Streamlit dashboard entry point.

Run with: ``streamlit run src/mrds/dashboard/app.py``. The Runs, Trends,
Regressions, and Baselines pages appear in the sidebar (see ``pages/``).
"""

from __future__ import annotations

import streamlit as st

from mrds.dashboard._shared import get_data, render_page_help

st.set_page_config(page_title="MRDS Dashboard", layout="wide")
st.title("Model Regression Detection System")
st.caption("Read-only view of evaluation history, trends, regressions, and baselines.")

st.info(
    "**A safety net for AI features.** Just as unit tests and CI stop broken code from "
    "shipping, MRDS runs an AI feature against a fixed set of hand-labeled examples, scores "
    "the results, and compares each new run against a trusted 'known-good' run (the "
    "*baseline*). If quality drops too far, deployments are blocked."
)

# Detailed reference lives in the sidebar so it stays visible while scrolling.
render_page_help("home")

data = get_data()
features = data.features()

if not features:
    st.info("No runs recorded yet. Use the CLI: `mrds evaluate --feature <name>`.")
else:
    st.metric("Features under test", len(features))
    for feature in features:
        st.write(f"- **{feature}** — {len(data.runs(feature))} run(s)")
    st.write("Open a page from the sidebar: **Runs**, **Trends**, **Regressions**, **Baselines**.")
