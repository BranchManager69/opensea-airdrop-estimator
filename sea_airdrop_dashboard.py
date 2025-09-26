import html
import math
import textwrap
from typing import Iterable, List

import altair as alt
import streamlit as st

from app.config import (
    COHORT_CONFIG,
    DEFAULT_REVEAL_DURATION,
    DEMO_WALLET,
    TOTAL_SUPPLY,
    resolve_page_icon,
)
from app.state import (
    bootstrap_session_state,
    sync_cohort_selection_from_query,
)
from app.ui.layout import (
    inject_global_styles,
    render_header,
)
from app.ui.cohort import render_cohort_selector
from app.ui.inputs import render_input_panel
from app.ui.wallet import render_wallet_section
from app.ui.reveal import run_reveal_presentation
from app.calculations import (
    build_heatmap_data,
    build_share_table,
    compute_scenario,
    determine_percentile_band,
    format_percentile_option,
    generate_percentile_options,
    snap_value_to_options,
)


st.set_page_config(
    page_title="Sea Mom",
    page_icon=resolve_page_icon(),
    layout="wide",
)

bootstrap_session_state()
params = st.query_params
sync_cohort_selection_from_query(params)

render_header()
inject_global_styles()

previous_selection = st.session_state.get("cohort_selection_prev")

cohort_context = render_cohort_selector()
cohort_selection = cohort_context.selection
distribution_rows = cohort_context.distribution_rows
cohort_estimate = cohort_context.estimate

if cohort_estimate:
    st.caption(
        f"{cohort_selection}: approximately {cohort_estimate:,} wallets qualify under this definition. "
        "Use the cohort size slider below to focus on your own OG definition."
    )

if (
    previous_selection is not None
    and previous_selection != cohort_selection
    and st.session_state.get("wallet_report")
    and distribution_rows
):
    summary = st.session_state["wallet_report"].get("summary", {})
    total_usd = float(summary.get("total_usd") or 0.0)
    band_info = determine_percentile_band(
        total_usd,
        distribution_rows,
        st.session_state.get("cohort_size", 100_000),
    )
    st.session_state["wallet_band"] = band_info
    if band_info:
        mid_percentile = (
            band_info.get("start_percentile", 0.0) + band_info.get("end_percentile", 0.0)
        ) / 2
        percentile_options = generate_percentile_options()
        snapped_percentile = snap_value_to_options(
            float(max(0.1, min(100.0, mid_percentile))),
            percentile_options,
        )
        st.session_state["tier_pct"] = snapped_percentile

st.session_state["cohort_selection_prev"] = cohort_selection

wallet_report, wallet_band = render_wallet_section(
    distribution_rows=distribution_rows,
)

inputs_context = render_input_panel(cohort_context)

og_pool_pct = inputs_context.og_pool_pct
fdv_billion = inputs_context.fdv_billion
cohort_size = inputs_context.cohort_size
tier_pct = inputs_context.tier_pct
share_options = inputs_context.share_options
fdv_sensitivity = inputs_context.fdv_sensitivity
clicked = inputs_context.clicked

total_supply = TOTAL_SUPPLY

if wallet_report and distribution_rows:
    summary_snapshot = wallet_report.get("summary", {})
    total_usd_snapshot = float(summary_snapshot.get("total_usd") or 0.0)
    recomputed_band = determine_percentile_band(
        total_usd_snapshot,
        distribution_rows,
        cohort_size,
    )
    st.session_state["wallet_band"] = recomputed_band
    wallet_band = recomputed_band


reveal_duration = DEFAULT_REVEAL_DURATION


token_price = (fdv_billion * 1_000_000_000) / total_supply
wallets_in_tier = max(1, math.floor(cohort_size * (tier_pct / 100)))
og_pool_tokens = total_supply * (og_pool_pct / 100)
featured_share = share_options[0]

selected_scenario = compute_scenario(
    total_supply=total_supply,
    og_pool_pct=og_pool_pct,
    fdv_billion=fdv_billion,
    cohort_size=cohort_size,
    tier_pct=tier_pct,
    share_pct=featured_share,
)

steps_for_reveal = [
    (
        "Token price",
        f"FDV ${fdv_billion:,.0f}B / {total_supply:,} SEA = ${token_price:,.2f} per token",
    ),
    (
        "OG pool allocation",
        f"{og_pool_pct}% of supply reserved for OGs → {og_pool_tokens:,.0f} SEA available to distribute",
    ),
    (
        "Tier sizing",
        f"{format_percentile_option(tier_pct)} equates to roughly {wallets_in_tier:,} wallets competing",
    ),
    (
        "Tier share assumption",
        f"Using a {featured_share}% slice of the OG pool for your tier gives {selected_scenario.tokens_per_wallet:,.0f} SEA each",
    ),
    (
        "Estimated payout",
        f"At ${token_price:,.2f}/SEA that works out to ≈ ${selected_scenario.usd_value:,.0f}",
    ),
]

current_signature = (
    og_pool_pct,
    fdv_billion,
    cohort_size,
    tier_pct,
    tuple(share_options),
    tuple(fdv_sensitivity),
)

if clicked:
    run_reveal_presentation(steps_for_reveal, reveal_duration)
    st.session_state.has_revealed_once = True
    st.session_state.last_reveal_signature = current_signature
    st.rerun()

hero_container = st.container()

def _format_step_detail(text: str) -> str:
    return html.escape(text)


def render_hero() -> None:
    usd_value = selected_scenario.usd_value
    sea_amount = selected_scenario.tokens_per_wallet

    with hero_container:
        hero_html = textwrap.dedent(
            f"""
            <div style="background: radial-gradient(circle at top left, #04111d, #0c345d); color: #ffffff; padding: 2.5rem; border-radius: 18px; text-align: center; margin-top: 1.5rem;">
                <div style="font-size:0.85rem; letter-spacing:0.18em; text-transform:uppercase; opacity:0.75;">Estimated payout</div>
                <div style="font-size:3.1rem; font-weight:700; margin:0.65rem 0;">${usd_value:,.0f}</div>
                <div style="font-size:1.15rem; opacity:0.9;">≈ {sea_amount:,.0f} SEA at ${token_price:,.2f} per token</div>
                <div style="margin-top:1.1rem; font-size:0.95rem; opacity:0.85;">Featured tier captures {featured_share}% of the OG pool.</div>
            </div>
            """
        )
        st.markdown(hero_html, unsafe_allow_html=True)

        insights = [
            (
                "Token price",
                f"${token_price:,.2f}",
                "Per SEA",
            ),
            (
                "OG pool",
                f"{og_pool_tokens:,.0f} SEA",
                "Allocated to OG cohort",
            ),
            (
                "Wallets in tier",
                f"{wallets_in_tier:,}",
                f"{format_percentile_option(tier_pct)} band",
            ),
        ]
        insight_cards_html = "\n".join(
            textwrap.dedent(
                f"""
                <div class='insight-card'>
                    <h4>{html.escape(label)}</h4>
                    <div class='value'>{html.escape(value)}</div>
                    <div class='hint'>{html.escape(hint)}</div>
                </div>
                """
            ).strip()
            for label, value, hint in insights
        )
        st.markdown(
            f"<div class='insight-grid'>{insight_cards_html}</div>",
            unsafe_allow_html=True,
        )

        steps_html = "\n".join(
            textwrap.dedent(
                f"""
                <li class='stepper-item'>
                    <div class='stepper-index'>{idx}</div>
                    <div class='stepper-content'>
                        <div class='title'>{html.escape(title)}</div>
                        <div class='detail'>{_format_step_detail(detail)}</div>
                    </div>
                </li>
                """
            ).strip()
            for idx, (title, detail) in enumerate(steps_for_reveal, start=1)
        )
        stepper_html = textwrap.dedent(
            f"""
            <div class='stepper'>
                <h4>How we got here</h4>
                <ul class='stepper-list'>
                    {steps_html}
                </ul>
            </div>
            """
        )
        st.markdown(stepper_html, unsafe_allow_html=True)


if st.session_state.has_revealed_once:
    inputs_changed = False
    if (
        st.session_state.last_reveal_signature is not None
        and st.session_state.last_reveal_signature != current_signature
    ):
        inputs_changed = True
        st.session_state.last_reveal_signature = current_signature

    if inputs_changed:
        st.info("Inputs updated — the estimate refreshes instantly.")

    render_hero()
