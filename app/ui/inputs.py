"""Input controls for the airdrop estimator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import streamlit as st

from app.calculations import (
    format_percentile_option,
    generate_percentile_options,
)
from app.config import TOTAL_SUPPLY


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

    st.markdown("### Airdrop assumptions")
    st.caption(
        "Defaults reflect my baseline expectations from professional experience and past comparable TGEs."
    )

    st.markdown("#### Launch valuation")
    valuation_cols = st.columns([2, 3])
    with valuation_cols[0]:
        st.caption("What will SEA's fully diluted valuation be at launch?")
    with valuation_cols[1]:
        fdv_options = [2, 3, 4, 5, 6, 7]
        fdv_range = f"${min(fdv_options)}B – ${max(fdv_options)}B"
        st.markdown(
            f"<div class='slider-header'><span>Launch FDV ($B)</span><span class='range'>{fdv_range}</span></div>",
            unsafe_allow_html=True,
        )
        fdv_billion = float(
            st.select_slider(
                "Launch FDV slider",
                options=fdv_options,
                format_func=lambda val: f"${val}B",
                key="fdv_billion",
                label_visibility="collapsed",
            )
        )

    st.markdown("#### OG pool size")
    og_cols = st.columns([2, 3])
    with og_cols[0]:
        st.caption("How much SEA will be reserved for OG users?")
    with og_cols[1]:
        st.markdown(
            "<div class='slider-header'><span>OG/community allocation (%)</span><span class='range'>10% – 25%</span></div>",
            unsafe_allow_html=True,
        )
        og_pool_pct = st.slider(
            "OG allocation slider",
            min_value=10,
            max_value=25,
            step=1,
            key="og_pool_pct",
            label_visibility="collapsed",
        )
        allocation_pct = og_pool_pct / 100.0
        tokens_allocated = allocation_pct * TOTAL_SUPPLY
        clamped_alloc = max(0.0, min(100.0, og_pool_pct))
        st.markdown(
            f"""
            <div class='allocation-gauge'>
                <div class='allocation-gauge-marker' style='left: {clamped_alloc:.2f}%;'>
                    <span class='label'>{og_pool_pct:.0f}% · {tokens_allocated:,.0f} SEA</span>
                    <span class='pin'></span>
                </div>
                <div class='allocation-gauge-track'></div>
                <div class='allocation-gauge-legend'>
                    <span>0% (0 SEA)</span>
                    <span>50% ({TOTAL_SUPPLY * 0.5:,.0f} SEA)</span>
                    <span>100% ({TOTAL_SUPPLY:,.0f} SEA)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### Personal positioning")
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

    slider_options = list(reversed(percentile_options))

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
            st.caption(
                "You haven’t provided your wallet yet. Best guess of how your activity compares to other OGs?"
            )

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

        percentile_min = min(percentile_options)
        percentile_max = max(percentile_options)
        pct_range = (
            f"{format_percentile_option(percentile_min)} – {format_percentile_option(percentile_max)}"
        )
        st.markdown(
            f"<div class='slider-header'><span>Your percentile band (%)</span><span class='range'>{pct_range}</span></div>",
            unsafe_allow_html=True,
        )
        tier_pct = st.select_slider(
            "Percentile band slider",
            options=slider_options,
            format_func=format_percentile_option,
            disabled=from_wallet and not manual_override,
            key="tier_pct",
            label_visibility="collapsed",
        )
        range_span = max(percentile_max - percentile_min, 1e-6)
        normalized = (float(tier_pct) - percentile_min) / range_span
        normalized = max(0.0, min(1.0, normalized))
        clamped_pct = 100.0 - normalized * 100.0
        marker_label = format_percentile_option(float(tier_pct))
        broad_label = format_percentile_option(percentile_max)
        elite_label = format_percentile_option(percentile_min)
        st.markdown(
            f"""
            <div class='percentile-gauge'>
                <div class='percentile-gauge-marker' style='left: {clamped_pct:.2f}%;'>
                    <span class='label'>{marker_label}</span>
                    <span class='pin'></span>
                </div>
                <div class='percentile-gauge-track'></div>
                <div class='percentile-gauge-legend'>
                    <span>Broad ({broad_label})</span>
                    <span>Middle (Top 50%)</span>
                    <span>Elite ({elite_label})</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not from_wallet or manual_override:
        st.session_state["tier_pct_source"] = {
            "value": tier_pct,
            "from_wallet": False,
        }

    st.markdown("\n")
    share_options = [20, 30, 40]

    fdv_candidates = {
        max(2.0, fdv_billion - 1.0),
        float(fdv_billion),
        min(7.0, fdv_billion + 1.0),
    }
    fdv_sensitivity = sorted(fdv_candidates)

    summary_cols = st.columns(3)
    summary_cols[0].metric("OG allocation", f"{og_pool_pct}%")
    summary_cols[1].metric("Launch FDV", f"${fdv_billion:.0f}B")
    summary_cols[2].metric("Percentile", format_percentile_option(tier_pct))

    has_wallet_report = bool(st.session_state.get("wallet_report"))
    button_disabled = not has_wallet_report

    with st.container():
        left_spacer, button_area, right_spacer = st.columns([2, 3, 2])
        with button_area:
            clicked = st.button(
                "Generate my Sea Mom projection",
                key="estimate_cta",
                type="primary",
                use_container_width=True,
                disabled=button_disabled,
            )

    return InputsContext(
        og_pool_pct=og_pool_pct,
        fdv_billion=fdv_billion,
        tier_pct=tier_pct,
        share_options=share_options,
        fdv_sensitivity=fdv_sensitivity,
        clicked=clicked,
    )
