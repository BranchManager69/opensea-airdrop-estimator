"""Input controls for the airdrop estimator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import streamlit as st

from app.calculations import (
    format_percentile_option,
    generate_percentile_options,
    snap_value_to_options,
)


@dataclass
class InputsContext:
    og_pool_pct: int
    fdv_billion: float
    cohort_size: int
    tier_pct: float
    share_options: List[float]
    fdv_sensitivity: List[float]
    clicked: bool


def render_input_panel(*, slider_options: List[int], slider_default: int) -> InputsContext:
    """Render sliders, scenario toggles, and the call-to-action button."""

    clicked = False

    with st.container():
        top_row = st.columns(4)

        with top_row[0]:
            st.markdown("**OG/community allocation (%)**")
            st.caption("Portion of supply earmarked for historical users.")
            og_pool_pct = st.slider(
                "OG/community allocation (%)",
                min_value=10,
                max_value=25,
                step=1,
                label_visibility="collapsed",
                key="og_pool_pct",
            )

        with top_row[1]:
            st.markdown("**Launch FDV ($B)**")
            st.caption("Fully diluted valuation at token generation event.")
            fdv_billion = float(
                st.select_slider(
                    "Launch FDV ($B)",
                    options=[2, 3, 4, 5, 6, 7],
                    format_func=lambda val: f"${val}B",
                    label_visibility="collapsed",
                    key="fdv_billion",
                )
            )

        with top_row[2]:
            st.markdown("**OG cohort size (wallets)**")
            st.caption("Estimated wallets eligible for OG rewards.")
            if "cohort_size" not in st.session_state:
                snapped_default = snap_value_to_options(float(slider_default), slider_options)
                st.session_state["cohort_size"] = int(snapped_default)
            current_value = st.session_state["cohort_size"]
            if current_value not in slider_options:
                nearest = min(slider_options, key=lambda opt: abs(opt - current_value))
                st.session_state["cohort_size"] = nearest
                current_value = nearest
            cohort_size = st.select_slider(
                "OG cohort size (wallets)",
                options=slider_options,
                format_func=lambda val: f"{val:,}",
                label_visibility="collapsed",
                key="cohort_size",
            )

        with top_row[3]:
            st.markdown("**Your percentile band (%)**")
            st.caption("Where you believe you sit within OGs.")
            percentile_options = generate_percentile_options()
            current_tier = st.session_state.get("tier_pct", percentile_options[0])
            if current_tier not in percentile_options:
                st.session_state["tier_pct"] = snap_value_to_options(
                    float(current_tier),
                    percentile_options,
                )
            tier_pct = st.select_slider(
                "Your percentile band (%)",
                options=percentile_options,
                format_func=format_percentile_option,
                label_visibility="collapsed",
                key="tier_pct",
            )

        st.markdown("---")

        scenario_cols = st.columns(2)
        with scenario_cols[0]:
            st.markdown("**Tier share comparisons**")
            default_share_options = [20, 30, 40]
            share_options = st.multiselect(
                "Tier share percentages to compare",
                options=[10, 15, 20, 25, 30, 35, 40, 45, 50],
                default=default_share_options,
            )
            if not share_options:
                share_options = default_share_options
            st.caption("The first selection powers the featured scenario.")

        with scenario_cols[1]:
            st.markdown("**FDV sensitivities**")
            fdv_sensitivity = st.multiselect(
                "FDV points ($B)",
                options=[3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
                default=[3.0, 4.0, 5.0],
            )
            if fdv_billion not in fdv_sensitivity:
                fdv_sensitivity.append(fdv_billion)
                fdv_sensitivity = sorted(set(fdv_sensitivity))
            st.caption("Optional extra FDV points you might want to analyze later.")

    with st.container():
        left_spacer, button_area, right_spacer = st.columns([3, 2, 3])
        with button_area:
            clicked = st.button(
                "Estimate my airdrop",
                key="estimate_cta",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.has_revealed_once,
            )

    return InputsContext(
        og_pool_pct=og_pool_pct,
        fdv_billion=fdv_billion,
        cohort_size=cohort_size,
        tier_pct=tier_pct,
        share_options=share_options,
        fdv_sensitivity=fdv_sensitivity,
        clicked=clicked,
    )
