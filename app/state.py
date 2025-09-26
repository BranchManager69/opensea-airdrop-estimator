"""Session-state helpers for Sea Mom."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from .config import COHORT_CONFIG

SESSION_DEFAULTS = {
    "tier_pct": 10.0,
    "cohort_size": 100_000,
    "og_pool_pct": 15,
    "fdv_billion": 4,
    "has_revealed_once": False,
    "last_reveal_signature": None,
}


def bootstrap_session_state() -> None:
    """Ensure frequently used keys exist in ``st.session_state``."""

    for key, value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def sync_cohort_selection_from_query(params: Mapping[str, Any]) -> None:
    """Populate the cohort selection based on the current query string."""

    slug_values = params.get("cohort") if hasattr(params, "get") else None
    if isinstance(slug_values, (list, tuple)):
        slug_param = slug_values[0] if slug_values else None
    else:
        slug_param = slug_values

    if not slug_param:
        return

    for display_name, config in COHORT_CONFIG.items():
        if config["slug"] == slug_param:
            st.session_state["cohort_selection"] = display_name
            break
