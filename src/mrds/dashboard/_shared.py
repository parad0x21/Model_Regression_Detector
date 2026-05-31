"""Shared Streamlit helpers for the dashboard pages."""

from __future__ import annotations

import streamlit as st

from mrds.config.settings import get_settings
from mrds.dashboard.data import DashboardData
from mrds.db import EvaluationStore, open_database
from mrds.demo import seed_demo


@st.cache_resource
def get_data() -> DashboardData:
    """Return a process-wide read-only data accessor (cached across reruns).

    In demo mode (``MRDS_DEMO=true``) with an empty database, deterministic offline
    demo data is seeded once before serving. Otherwise the dashboard never writes.
    """
    store = EvaluationStore(open_database(check_same_thread=False))
    if get_settings().demo_mode and not store.runs.features():
        with st.spinner("Seeding deterministic demo data (offline, one-time)…"):
            seed_demo(store)
    return DashboardData(store)


def feature_selector(data: DashboardData, *, key: str) -> str | None:
    """Render a feature picker; returns the selected feature or None if there are none."""
    features = data.features()
    if not features:
        st.info("No evaluation runs recorded yet. Run `mrds evaluate --feature <name>` first.")
        return None
    return st.selectbox("Feature", features, key=key)
