import math
from typing import Any, Dict

import streamlit as st

from app.config import (
    DEFAULT_REVEAL_DURATION,
    TOTAL_SUPPLY,
    resolve_page_icon,
)
from app.state import bootstrap_session_state
from app.ui.layout import inject_global_styles, render_header
from app.ui.cohort import build_slider_defaults, load_cohort_data, render_scenario_cards
from app.ui.inputs import render_input_panel
from app.ui.wallet import render_wallet_section
from app.ui.reveal import run_reveal_presentation
from app.ui.share import render_share_panel
from app.ui.results import ScenarioSnapshot, render_results
from app.calculations import (
    build_heatmap_data,
    build_share_table,
    compute_scenario,
    determine_percentile_band,
    format_percentile_option,
)


st.set_page_config(
    page_title="Sea Mom",
    page_icon=resolve_page_icon(),
    layout="wide",
)

bootstrap_session_state()
params = st.query_params

wallet_values = params.get("wallet")
if isinstance(wallet_values, (list, tuple)):
    wallet_param = wallet_values[0] if wallet_values else None
else:
    wallet_param = wallet_values

wallet_param = wallet_param.strip() if wallet_param else None

render_header()
inject_global_styles()

cohort_data = load_cohort_data()
if not cohort_data:
    st.error("No cohort distributions found. Please update the data files and refresh.")
    st.stop()

primary_name = next(iter(cohort_data))
primary_cohort = cohort_data[primary_name]
slider_options, slider_default = build_slider_defaults(primary_cohort)
baseline_rows = primary_cohort.rows

wallet_report, wallet_band = render_wallet_section(
    distribution_rows=baseline_rows,
    preset_wallet=wallet_param,
    auto_fetch=bool(wallet_param),
)

inputs_context = render_input_panel(
    slider_options=slider_options,
    slider_default=slider_default,
)

og_pool_pct = inputs_context.og_pool_pct
fdv_billion = inputs_context.fdv_billion
cohort_size = inputs_context.cohort_size
tier_pct = inputs_context.tier_pct
share_options = inputs_context.share_options
fdv_sensitivity = inputs_context.fdv_sensitivity
clicked = inputs_context.clicked

if not share_options:
    share_options = [20, 30, 40]
featured_share = share_options[0]

total_supply = TOTAL_SUPPLY
token_price = (fdv_billion * 1_000_000_000) / total_supply

summary_snapshot: Dict[str, Any] = {}
total_usd_snapshot = 0.0
if wallet_report and baseline_rows:
    summary_snapshot = wallet_report.get("summary", {}) or {}
    total_usd_snapshot = float(summary_snapshot.get("total_usd") or 0.0)
    recomputed_band = determine_percentile_band(
        total_usd_snapshot,
        baseline_rows,
        cohort_size,
    )
    st.session_state["wallet_band"] = recomputed_band
    wallet_band = recomputed_band

base_estimate = primary_cohort.estimate or slider_default or cohort_size or 1
if base_estimate <= 0:
    base_estimate = max(cohort_size, 1)

scenario_cards = []
primary_result = None
primary_cohort_size = cohort_size
primary_wallets_in_tier = max(1, math.floor(primary_cohort_size * (tier_pct / 100)))
primary_full_label = primary_cohort.config.get("title", primary_name)
timeline_label = primary_cohort.config.get("timeline_label")
if timeline_label:
    primary_full_label = f"{primary_full_label} · {timeline_label}"

for name, data in cohort_data.items():
    estimate = data.estimate or base_estimate
    factor = estimate / base_estimate if base_estimate else 1.0
    scenario_cohort_size = max(1, int(round(cohort_size * factor)))
    scenario_result = compute_scenario(
        total_supply=total_supply,
        og_pool_pct=og_pool_pct,
        fdv_billion=fdv_billion,
        cohort_size=scenario_cohort_size,
        tier_pct=tier_pct,
        share_pct=featured_share,
    )
    wallets_in_tier_value = max(1, math.floor(scenario_cohort_size * (tier_pct / 100)))

    band_text = ""
    if wallet_report and data.rows:
        band = determine_percentile_band(
            total_usd_snapshot,
            data.rows,
            scenario_cohort_size,
        )
        if band:
            start_pct = band.get("start_percentile")
            end_pct = band.get("end_percentile")
            if start_pct is not None and end_pct is not None:
                band_text = f"Wallet percentile: {start_pct:.1f}% – {end_pct:.1f}%"

    title = data.config.get("title", name)
    subtitle_bits = [data.config.get("timeline_label"), data.config.get("tagline")]
    subtitle = " · ".join([bit for bit in subtitle_bits if bit])
    if not subtitle:
        subtitle = data.name
    wallets_label = f"Wallets modelled: {scenario_cohort_size:,}"
    if data.estimate:
        wallets_label += f" (est. {data.estimate:,})"

    full_label = title
    timeline = data.config.get("timeline_label")
    if timeline:
        full_label = f"{full_label} · {timeline}"

    scenario_cards.append(
        {
            "title": title,
            "subtitle": subtitle,
            "payout_text": f"≈ ${scenario_result.usd_value:,.0f}",
            "tokens_text": f"Ξ{scenario_result.tokens_per_wallet:,.0f} per wallet · {featured_share:.0f}% share",
            "wallets_text": wallets_label,
            "band_text": band_text,
            "is_primary": name == primary_name,
            "cohort_size": scenario_cohort_size,
            "usd_value": scenario_result.usd_value,
            "tokens_value": scenario_result.tokens_per_wallet,
            "full_label": full_label,
        }
    )

    if name == primary_name:
        primary_result = scenario_result
        primary_cohort_size = scenario_cohort_size
        primary_wallets_in_tier = wallets_in_tier_value
        if full_label:
            primary_full_label = full_label

if primary_result is None:
    primary_result = compute_scenario(
        total_supply=total_supply,
        og_pool_pct=og_pool_pct,
        fdv_billion=fdv_billion,
        cohort_size=cohort_size,
        tier_pct=tier_pct,
        share_pct=featured_share,
    )
    primary_cohort_size = cohort_size
    primary_wallets_in_tier = max(1, math.floor(primary_cohort_size * (tier_pct / 100)))

steps_for_reveal = [
    (
        "Token price",
        f"FDV ${fdv_billion:,.0f}B / {total_supply:,} SEA = ${token_price:,.2f} per token",
    ),
    (
        "OG pool allocation",
        f"{og_pool_pct}% of supply reserved for OGs → {total_supply * (og_pool_pct / 100):,.0f} SEA available to distribute",
    ),
    (
        "Tier sizing",
        f"{format_percentile_option(tier_pct)} equates to roughly {primary_wallets_in_tier:,} wallets competing",
    ),
    (
        "Tier share assumption",
        f"Using a {featured_share}% slice of the OG pool for your tier gives {primary_result.tokens_per_wallet:,.0f} SEA each",
    ),
    (
        "Estimated payout",
        f"At ${token_price:,.2f}/SEA that works out to ≈ ${primary_result.usd_value:,.0f}",
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
    wallets_in_tier=primary_wallets_in_tier,
    og_pool_tokens=total_supply * (og_pool_pct / 100),
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

reveal_duration = DEFAULT_REVEAL_DURATION

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
        selected_scenario=primary_result,
        reveal_signature=current_signature,
    )

    render_scenario_cards(scenario_cards)

    primary_card = next((card for card in scenario_cards if card.get("is_primary")), None)
    primary_label = primary_full_label
    primary_cohort_wallets = primary_cohort_size
    if primary_card:
        primary_label = primary_card.get("full_label", primary_label)
        primary_cohort_wallets = primary_card.get("cohort_size", primary_cohort_size)

    render_share_panel(
        current_signature=current_signature,
        cohort_label=primary_label,
        cohort_wallets=primary_cohort_wallets,
        og_pool_pct=og_pool_pct,
        fdv_billion=fdv_billion,
        tier_pct=tier_pct,
        featured_share=featured_share,
        token_price=token_price,
        scenario_usd=primary_result.usd_value,
        scenario_tokens=primary_result.tokens_per_wallet,
        wallet_report=wallet_report,
    )
