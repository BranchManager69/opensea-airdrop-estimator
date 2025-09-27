"""Input controls for the airdrop estimator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import streamlit as st

from app.calculations import (
    format_percentile_option,
    generate_percentile_options,
)


@dataclass
class InputsContext:
    og_pool_pct: int
    fdv_billion: float
    tier_pct: float
    share_options: List[float]
    fdv_sensitivity: List[float]
    clicked: bool


def render_input_panel() -> InputsContext:
    """Render sliders, scenario toggles, and the call-to-action button."""

    with st.expander("Launch dynamics", expanded=True):
        launch_cols = st.columns(2)
        with launch_cols[0]:
            st.caption("Share of total supply earmarked for the OG crowd.")
            og_pool_pct = st.slider(
                "OG/community allocation (%)",
                min_value=10,
                max_value=25,
                step=1,
                key="og_pool_pct",
            )
        with launch_cols[1]:
            st.caption("Fully diluted valuation at token generation event.")
            fdv_billion = float(
                st.select_slider(
                    "Launch FDV ($B)",
                    options=[2, 3, 4, 5, 6, 7],
                    format_func=lambda val: f"${val}B",
                    key="fdv_billion",
                )
            )

    with st.expander("Personal positioning", expanded=True):
        percentile_options = generate_percentile_options()
        auto_source = st.session_state.get("tier_pct_source", {})
        auto_value = auto_source.get("value")
        if auto_source.get("from_wallet") and auto_value is not None:
            try:
                auto_float = float(auto_value)
            except (TypeError, ValueError):
                auto_float = None
            if auto_float is not None and auto_float not in percentile_options:
                percentile_options = sorted(percentile_options + [auto_float])

        current_tier = st.session_state.get("tier_pct", percentile_options[0])
        if current_tier not in percentile_options:
            st.session_state["tier_pct"] = percentile_options[0]
            current_tier = percentile_options[0]

        from_wallet = bool(auto_source.get("from_wallet"))

        info_col, control_col = st.columns([2, 3])
        with info_col:
            if from_wallet:
                st.caption(
                    f"Wallet history suggests {format_percentile_option(current_tier)}. Toggle manual mode to override."
                )
            else:
                st.caption("Where do you realistically sit among OG traders?")

        with control_col:
            if from_wallet:
                manual_override = st.checkbox(
                    "Adjust percentile manually",
                    value=st.session_state.get("tier_pct_manual", False),
                    key="tier_pct_manual_toggle",
                )
                st.session_state["tier_pct_manual"] = manual_override
            else:
                st.session_state["tier_pct_manual"] = True
                manual_override = True

            tier_pct = st.select_slider(
                "Your percentile band (%)",
                options=percentile_options,
                format_func=format_percentile_option,
                disabled=from_wallet and not manual_override,
                key="tier_pct",
            )

        if not from_wallet or manual_override:
            st.session_state["tier_pct_source"] = {
                "value": tier_pct,
                "from_wallet": False,
            }

    with st.expander("Token math", expanded=False):
        scenario_cols = st.columns(2)
        with scenario_cols[0]:
            st.caption("Pick comparison points for how much of the OG pool your tier captures.")
            default_share_options = [20, 30, 40]
            share_options = st.multiselect(
                "Tier share percentages to compare",
                options=[10, 15, 20, 25, 30, 35, 40, 45, 50],
                default=default_share_options,
            )
            if not share_options:
                share_options = default_share_options
            st.caption("First value drives the featured scenario.")

        with scenario_cols[1]:
            st.caption("Add extra FDV points for the comparison heatmap.")
            fdv_sensitivity = st.multiselect(
                "FDV points ($B)",
                options=[3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
                default=[3.0, 4.0, 5.0],
            )
            if fdv_billion not in fdv_sensitivity:
                fdv_sensitivity.append(fdv_billion)
                fdv_sensitivity = sorted(set(fdv_sensitivity))

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
        tier_pct=tier_pct,
        share_options=share_options,
        fdv_sensitivity=fdv_sensitivity,
        clicked=clicked,
    )
