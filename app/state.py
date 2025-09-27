"""Session-state helpers for Sea Mom."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

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
