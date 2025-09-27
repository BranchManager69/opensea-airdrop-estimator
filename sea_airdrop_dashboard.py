import math
import textwrap
from typing import Any, Dict, List

import altair as alt
import pandas as pd
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
from app.share_service import ShareServiceError
from app.ui.share import ensure_share_card, render_share_panel
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

summary_placeholder = st.empty()

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

inputs_context = render_input_panel()

og_pool_pct = inputs_context.og_pool_pct
fdv_billion = inputs_context.fdv_billion
tier_pct = inputs_context.tier_pct
share_options = inputs_context.share_options
fdv_sensitivity = inputs_context.fdv_sensitivity
clicked = inputs_context.clicked

if "cohort_size" not in st.session_state:
    st.session_state["cohort_size"] = slider_default

cohort_size = st.session_state["cohort_size"]

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
scenario_bands: Dict[str, Dict[str, Any]] = {}
curve_rows: List[Dict[str, float]] = []
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
    start_pct = None
    end_pct = None
    band_mid = None
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
                band_mid = (start_pct + end_pct) / 2

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

    scenario_bands[name] = {
        "label": full_label,
        "start": start_pct,
        "end": end_pct,
        "mid": band_mid,
        "cohort_size": scenario_cohort_size,
    }

    card_curve_points: List[Dict[str, float]] = []

    for row in data.rows:
        percentile = row.get("usd_percentile_rank")
        if percentile is None:
            continue
        try:
            percentile_val = float(percentile)
        except (TypeError, ValueError):
            continue
        min_usd = row.get("min_total_usd")
        max_usd = row.get("max_total_usd")
        try:
            min_usd_val = float(min_usd) if min_usd is not None else 0.0
        except (TypeError, ValueError):
            min_usd_val = 0.0
        try:
            max_usd_val = float(max_usd) if max_usd is not None else min_usd_val
        except (TypeError, ValueError):
            max_usd_val = min_usd_val
        usd_value = max(min_usd_val, max_usd_val)
        if usd_value <= 0 or percentile_val <= 0:
            continue
        point_payload = {
            "scenario": full_label,
            "percentile": percentile_val,
            "usd": usd_value,
            "min_usd": min_usd_val,
            "max_usd": max_usd_val,
        }
        card_curve_points.append(point_payload)
        curve_rows.append(point_payload)

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
            "curve_points": card_curve_points,
            "highlight_mid": band_mid,
            "highlight_usd": total_usd_snapshot if total_usd_snapshot > 0 else None,
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

primary_card = next((card for card in scenario_cards if card.get("is_primary")), None)
primary_label = primary_full_label
primary_cohort_wallets = primary_cohort_size
if primary_card:
    primary_label = primary_card.get("full_label", primary_label)
    primary_cohort_wallets = primary_card.get("cohort_size", primary_cohort_wallets)

st.session_state["scenario_bands"] = scenario_bands
st.session_state["scenario_curves"] = curve_rows

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

prefetched_card: Dict[str, Any] | None = None
share_payload: Dict[str, Any] | None = None

if clicked:
    run_reveal_presentation(steps_for_reveal, reveal_duration)
    st.session_state.has_revealed_once = True
    st.session_state.last_reveal_signature = current_signature
    st.rerun()

if st.session_state.has_revealed_once:
    last_signature = st.session_state.get("last_reveal_signature")
    if last_signature is not None and last_signature != current_signature:
        st.info("Inputs updated — the estimate refreshes instantly.")

    wallet_address = st.session_state.get("wallet_address")
    if (
        wallet_report
        and wallet_report.get("summary")
        and wallet_address
        and wallet_report.get("collections") is not None
    ):
        summary = wallet_report.get("summary", {})
        trade_count = int(float(summary.get("trade_count") or 0))
        total_eth = float(summary.get("total_eth") or 0.0)
        total_usd = float(summary.get("total_usd") or 0.0)
        last_trade = summary.get("last_trade") or summary.get("last_activity")
        percentile_label = format_percentile_option(tier_pct)

        share_payload = {
            "wallet": wallet_address,
            "payoutUsd": float(primary_result.usd_value),
            "payoutTokens": float(primary_result.tokens_per_wallet),
            "tokenPrice": float(token_price),
            "cohortLabel": primary_label,
            "cohortWallets": int(primary_cohort_wallets or 0),
            "percentileLabel": percentile_label,
            "sharePct": float(featured_share),
            "fdvBillion": float(fdv_billion),
            "ogPoolPct": float(og_pool_pct),
            "tradeCount": trade_count,
            "totalEth": total_eth,
            "totalUsd": total_usd,
            "asOf": last_trade,
        }

        try:
            prefetched_card = ensure_share_card(
                signature=current_signature,
                payload=share_payload,
                show_spinner=False,
            )
        except ShareServiceError as share_err:
            st.warning(f"Share preview unavailable: {share_err}")
            prefetched_card = None

    primary_band_info = scenario_bands.get(primary_name, {})
    start_pct = primary_band_info.get("start")
    end_pct = primary_band_info.get("end")
    percentile_text = None
    if start_pct is not None and end_pct is not None:
        percentile_text = f"{start_pct:.1f}% – {end_pct:.1f}%"
    elif wallet_band:
        start_pct = wallet_band.get("start_percentile")
        end_pct = wallet_band.get("end_percentile")
        if start_pct is not None and end_pct is not None:
            percentile_text = f"{start_pct:.1f}% – {end_pct:.1f}%"

    preview_card = prefetched_card or st.session_state.get("share_card_cache", {}).get(current_signature)
    preview_img = preview_card.get("image_url") if preview_card else None
    preview_link = preview_card.get("share_url") if preview_card else None

    with summary_placeholder.container():
        summary_html = textwrap.dedent(
            f"""
            <div class='results-banner'>
                <div class='results-banner-metrics'>
                    <div class='metric-block'>
                        <div class='metric-label'>Projected payout</div>
                        <div class='metric-value'>${primary_result.usd_value:,.0f}</div>
                        <div class='metric-hint'>≈ {primary_result.tokens_per_wallet:,.0f} SEA @ ${token_price:,.2f}</div>
                    </div>
                    <div class='metric-block'>
                        <div class='metric-label'>Percentile band</div>
                        <div class='metric-value'>{percentile_text or "Set your percentile"}</div>
                        <div class='metric-hint'>{primary_label}</div>
                    </div>
                </div>
                <div class='results-banner-share'>
                    {f"<img src='{preview_img}' alt='Sea Mom Flex preview' />" if preview_img else "<div class='share-placeholder'>Generate your Sea Mom Flex below.</div>"}
                    {f"<a href='{preview_link}' class='share-link' target='_blank'>Open share page</a>" if preview_link else ""}
                </div>
            </div>
            """
        )
        st.markdown(summary_html, unsafe_allow_html=True)

    render_results(
        scenario_snapshot=scenario_snapshot,
        selected_scenario=primary_result,
        reveal_signature=current_signature,
    )

    render_scenario_cards(
        scenario_cards,
        slider_options=slider_options,
    )

    curve_rows_state = st.session_state.get("scenario_curves", [])
    if curve_rows_state:
        curve_df = pd.DataFrame(curve_rows_state)
        curve_df = curve_df.dropna(subset=["percentile", "usd"])
        if not curve_df.empty:
            st.markdown("**Percentile positioning across cohorts**")
            curve_chart = (
                alt.Chart(curve_df)
                .mark_line()
                .encode(
                    x=alt.X("percentile:Q", title="Percentile (lower = more OG)"),
                    y=alt.Y(
                        "usd:Q",
                        title="Total USD volume",
                        scale=alt.Scale(type="log", domainMin=1),
                    ),
                    color=alt.Color("scenario:N", title="Cohort"),
                    tooltip=[
                        alt.Tooltip("scenario:N", title="Cohort"),
                        alt.Tooltip("percentile:Q", title="Percentile", format=".1f"),
                        alt.Tooltip("usd:Q", title="USD volume", format=",.0f"),
                        alt.Tooltip("min_usd:Q", title="Min USD", format=",.0f"),
                        alt.Tooltip("max_usd:Q", title="Max USD", format=",.0f"),
                    ],
                )
                .properties(height=320)
            )

            point_rows: List[Dict[str, float]] = []
            scenario_band_info = st.session_state.get("scenario_bands", {})
            if total_usd_snapshot > 0:
                for info in scenario_band_info.values():
                    mid_pct = info.get("mid")
                    label = info.get("label")
                    if mid_pct is not None and label:
                        point_rows.append(
                            {
                                "scenario": label,
                                "percentile": mid_pct,
                                "usd": total_usd_snapshot,
                            }
                        )

            if point_rows:
                point_df = pd.DataFrame(point_rows)
                point_chart = (
                    alt.Chart(point_df)
                    .mark_point(size=130, filled=True)
                    .encode(
                        x="percentile:Q",
                        y="usd:Q",
                        color=alt.Color("scenario:N", title="Cohort"),
                        tooltip=[
                            alt.Tooltip("scenario:N", title="Cohort"),
                            alt.Tooltip("percentile:Q", title="Wallet percentile", format=".1f"),
                            alt.Tooltip("usd:Q", title="Wallet volume", format=",.0f"),
                        ],
                    )
                )
                curve_chart = curve_chart + point_chart

            st.altair_chart(curve_chart, use_container_width=True)

    share_panel = st.container()
    with share_panel:
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
            precomputed_card=prefetched_card,
            payload=share_payload,
        )
