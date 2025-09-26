import math
import streamlit as st

from app.config import (
    DEFAULT_REVEAL_DURATION,
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
from app.ui.results import ScenarioSnapshot, render_results
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

share_table = build_share_table(
    share_options,
    total_supply=total_supply,
    og_pool_pct=og_pool_pct,
    fdv_billion=fdv_billion,
    cohort_size=cohort_size,
    tier_pct=tier_pct,
)

heatmap_df = build_heatmap_data(
    share_options,
    fdv_sensitivity,
    total_supply=total_supply,
    og_pool_pct=og_pool_pct,
    cohort_size=cohort_size,
    tier_pct=tier_pct,
)

scenario_snapshot = ScenarioSnapshot(
    token_price=token_price,
    wallets_in_tier=wallets_in_tier,
    og_pool_tokens=og_pool_tokens,
    featured_share=featured_share,
    tier_pct=tier_pct,
    selected_df=share_table,
    heatmap_df=heatmap_df,
    steps=steps_for_reveal,
)

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

if st.session_state.has_revealed_once:
    last_signature = st.session_state.get("last_reveal_signature")
    if last_signature is not None and last_signature != current_signature:
        st.info("Inputs updated — the estimate refreshes instantly.")

    render_results(
        scenario_snapshot=scenario_snapshot,
        selected_scenario=selected_scenario,
        reveal_signature=current_signature,
    )
