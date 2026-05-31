"""Shared Streamlit helpers for the dashboard pages."""

from __future__ import annotations

import os

import streamlit as st

from mrds.config.settings import Settings, get_settings
from mrds.dashboard.data import DashboardData
from mrds.dashboard.help_text import PAGE_HELP
from mrds.db import EvaluationStore, open_database
from mrds.demo import seed_demo

# Values accepted as a truthy MRDS_DEMO flag when read straight from the env.
_TRUTHY_DEMO = {"1", "true", "yes", "on"}


def _demo_enabled(settings: Settings) -> bool:
    """Whether to seed offline demo data, resilient to settings-layer quirks.

    Prefers the validated ``demo_mode`` field. If that field is unavailable on the
    resolved ``Settings`` instance (some pydantic-settings/Python combinations drop
    the ``validation_alias``-only field, which previously crashed the dashboard),
    fall back to reading ``MRDS_DEMO`` from the environment directly.
    """
    flag = getattr(settings, "demo_mode", None)
    if flag is not None:
        return bool(flag)
    return os.getenv("MRDS_DEMO", "").strip().lower() in _TRUTHY_DEMO


@st.cache_resource
def get_data() -> DashboardData:
    """Return a process-wide read-only data accessor (cached across reruns).

    In demo mode (``MRDS_DEMO=true``) with an empty database, deterministic offline
    demo data is seeded once before serving. Otherwise the dashboard never writes.
    """
    store = EvaluationStore(open_database(check_same_thread=False))
    if _demo_enabled(get_settings()) and not store.runs.features():
        with st.spinner("Seeding deterministic demo data (offline, one-time)…"):
            seed_demo(store)
    return DashboardData(store)


def render_page_help(page_key: str) -> None:
    """Render a page's guidance: a one-line caption in the main column, and a
    persistent reference in the sidebar.

    The sidebar stays fixed while the main content scrolls, so visitors can keep
    the explanations in view without scrolling back to the top.
    """
    help_ = PAGE_HELP[page_key]
    if help_.caption:
        st.caption(help_.caption)

    with st.sidebar:
        st.divider()
        st.markdown("### 📖 Page guide")
        if help_.overview:
            st.info(help_.overview)
        for title, body in help_.sections:
            with st.expander(title, expanded=True):
                st.markdown(body)


def feature_selector(data: DashboardData, *, key: str) -> str | None:
    """Render a feature picker; returns the selected feature or None if there are none."""
    features = data.features()
    if not features:
        st.info("No evaluation runs recorded yet. Run `mrds evaluate --feature <name>` first.")
        return None
    return st.selectbox("Feature", features, key=key)
