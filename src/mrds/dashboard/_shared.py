"""Shared Streamlit helpers for the dashboard pages."""

from __future__ import annotations

import streamlit as st

from mrds.dashboard.data import DashboardData
from mrds.db import EvaluationStore, open_database


@st.cache_resource
def get_data() -> DashboardData:
    """Return a process-wide read-only data accessor (cached across reruns)."""
    store = EvaluationStore(open_database(check_same_thread=False))
    return DashboardData(store)


def feature_selector(data: DashboardData, *, key: str) -> str | None:
    """Render a feature picker; returns the selected feature or None if there are none."""
    features = data.features()
    if not features:
        st.info("No evaluation runs recorded yet. Run `mrds evaluate --feature <name>` first.")
        return None
    return st.selectbox("Feature", features, key=key)
