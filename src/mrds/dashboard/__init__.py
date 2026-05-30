"""Read-only Streamlit dashboard over the SQLite system of record.

The data-access layer (:mod:`mrds.dashboard.data`) is Streamlit-free and testable;
the Streamlit entry script and pages live alongside it. Launch with:

    streamlit run src/mrds/dashboard/app.py
"""

from mrds.dashboard.data import DashboardData, TrendPoint

__all__ = ["DashboardData", "TrendPoint"]
