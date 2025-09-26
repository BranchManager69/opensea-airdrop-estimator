import html
import math
import textwrap
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

import altair as alt
import pandas as pd
import streamlit as st

from app.config import (
    COHORT_CONFIG,
    DEFAULT_REVEAL_DURATION,
    DEMO_WALLET,
    TOTAL_SUPPLY,
    resolve_page_icon,
)
from app.data_sources import (
    estimate_og_cohort_size,
    fetch_wallet_report,
    load_distribution,
)
from app.state import (
    bootstrap_session_state,
    sync_cohort_selection_from_query,
)
from app.ui.layout import (
    inject_global_styles,
    render_header,
)
from app.calculations import (
    build_heatmap_data,
    build_share_table,
    compute_scenario,
    determine_percentile_band,
    format_percentile_option,
    generate_cohort_slider_options,
    generate_percentile_options,
    round_to_step,
    round_up_to_step,
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

def run_reveal_presentation(steps: List[tuple[str, str]], duration_seconds: int) -> None:
    """Animate the reveal timeline with a progress bar and step narration."""

    timeline = st.container()
    progress = timeline.progress(0, text="Preparing SEA airdrop projection…")
    narration = timeline.empty()

    total_steps = max(len(steps), 1)
    # Avoid zero division and guarantee a minimum dwell per step.
    step_duration = max(duration_seconds / total_steps, 0.35)

    for idx, (title, detail) in enumerate(steps, start=1):
        progress.progress(
            int(idx / total_steps * 100),
            text=title,
        )
        narration.markdown(f"**{title}**\n\n{detail}")
        time.sleep(step_duration)

    progress.empty()
    narration.empty()
    st.success("Projection ready — scroll to view your estimated allocation.")


render_header()
inject_global_styles()

cohort_names = list(COHORT_CONFIG.keys())
available_cohorts = [name for name in cohort_names if COHORT_CONFIG[name]["path"].exists()]
default_cohort = (
    st.session_state.get("cohort_selection")
    or (available_cohorts[0] if available_cohorts else cohort_names[0])
)
if default_cohort not in cohort_names:
    default_cohort = cohort_names[0]

cohort_selection = st.session_state.get("cohort_selection", default_cohort)
if cohort_selection not in cohort_names:
    cohort_selection = default_cohort

previous_selection = st.session_state.get("cohort_selection_prev")

cohort_distributions: Dict[str, List[Dict[str, Any]]] = {}
cohort_totals: Dict[str, int] = {}
for name in cohort_names:
    rows = load_distribution(COHORT_CONFIG[name]["path"])
    cohort_distributions[name] = rows
    cohort_totals[name] = estimate_og_cohort_size(rows)

timeline_container = st.container()
with timeline_container:
    st.markdown("<div class='cohort-timeline'>", unsafe_allow_html=True)
    cards_html = []
    for name in cohort_names:
        conf = COHORT_CONFIG[name]
        total = cohort_totals.get(name, 0)
        total_text = f"{total:,} wallets" if total else "Loading…"
        selected_class = "selected" if name == cohort_selection else ""
        cards_html.append(
            f"<a class='cohort-card-link' href='?cohort={conf['slug']}'>"
            f"<div class='cohort-card {selected_class}'>"
            f"<span class='cohort-card-title'>{conf['title']}</span>"
            f"<span class='cohort-card-year'>{conf['timeline_label']} · {conf['tagline']}</span>"
            f"<span class='cohort-card-metric'>{total_text}</span>"
            "</div>"
            "</a>"
        )
    st.markdown(
        "<div class='cohort-cards-row'>" + "".join(cards_html) + "</div>",
        unsafe_allow_html=True,
    )
    selected_conf = COHORT_CONFIG[cohort_selection]
    if selected_conf.get("description"):
        st.markdown(
            f"<div class='cohort-description'>{selected_conf['description']}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

st.session_state["cohort_selection"] = cohort_selection
st.session_state["cohort_timeline"] = COHORT_CONFIG[cohort_selection]["timeline_label"]
current_slug = COHORT_CONFIG[cohort_selection]["slug"]
existing_slug = params.get("cohort")
if isinstance(existing_slug, (list, tuple)):
    existing_slug = existing_slug[0] if existing_slug else None
if existing_slug != current_slug:
    st.query_params["cohort"] = current_slug
selected_cohort_conf = COHORT_CONFIG[cohort_selection]
distribution_rows = cohort_distributions.get(cohort_selection, [])
cohort_estimate = 0

if distribution_rows:
    cohort_estimate = cohort_totals.get(cohort_selection, 0)
    if cohort_estimate:
        st.session_state["cohort_size_estimate"] = cohort_estimate
else:
    cohort_estimate = st.session_state.get("cohort_size_estimate", 0)

if cohort_estimate:
    st.caption(
        f"{cohort_selection}: approximately {cohort_estimate:,} wallets qualify under this definition. "
        "Use the cohort size slider below to focus on your own OG definition."
    )

if not distribution_rows:
    st.warning(
        f"Percentile distribution file missing for {cohort_selection}. "
        f"Expected at {selected_cohort_conf['path']}"
    )

slider_min = 50_000
slider_mid = 100_000
slider_max = 500_000

if cohort_estimate:
    slider_mid = round_to_step(max(slider_min, cohort_estimate), 5_000)
    slider_max = max(
        slider_max,
        round_up_to_step(cohort_estimate * 1.2, 5_000),
    )
    slider_mid = min(slider_max, slider_mid)

cohort_slider_options = generate_cohort_slider_options(
    min_val=slider_min,
    mid_val=slider_mid,
    max_val=slider_max,
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

wallet_holder = st.container()

with wallet_holder:
    st.markdown("**Lookup your OpenSea wallet**")
    default_wallet = st.session_state.get("wallet_input", DEMO_WALLET)
    wallet_address = st.text_input(
        "Wallet address",
        value=default_wallet,
        placeholder="0x...",
    )
    st.session_state["wallet_input"] = wallet_address
    fetch_cols = st.columns([1, 3])
    with fetch_cols[0]:
        fetch_clicked = st.button("Fetch history", type="secondary")

    if fetch_clicked:
        if not wallet_address:
            st.warning("Enter a wallet address to fetch OpenSea activity.")
        else:
            try:
                with st.spinner("Contacting Dune …"):
                    report = fetch_wallet_report(wallet_address)
                if not report or not report.get("summary"):
                    st.info("No OpenSea trades found for this wallet.")
                    st.session_state.pop("wallet_report", None)
                    st.session_state.pop("wallet_band", None)
                else:
                    st.session_state["wallet_report"] = report
                    summary = report["summary"]
                    total_usd = float(summary.get("total_usd") or 0.0)
                    current_cohort_value = st.session_state.get("cohort_size", 100_000)
                    band_info = determine_percentile_band(
                        total_usd,
                        distribution_rows,
                        current_cohort_value,
                    )
                    st.session_state["wallet_band"] = band_info
                    if band_info:
                        mid_percentile = (
                            band_info["start_percentile"] + band_info["end_percentile"]
                        ) / 2
                        st.session_state["tier_pct"] = float(
                            max(0.1, min(100.0, mid_percentile))
                        )
                    else:
                        st.info(
                            "This wallet’s volume falls outside the cohort size you selected. "
                            "Increase the cohort or adjust the OG definition to include it."
                        )
                    cohort_estimate = estimate_og_cohort_size(distribution_rows)
                    if cohort_estimate:
                        st.session_state["cohort_size_estimate"] = cohort_estimate
                    st.session_state["wallet_address"] = wallet_address
                    st.success("Wallet snapshot updated. Scroll down to view personalised metrics.")
            except RuntimeError as err:
                st.error(str(err))
            except requests.exceptions.RequestException as err:
                st.error(f"Failed to fetch wallet data: {err}")

wallet_report = st.session_state.get("wallet_report")
wallet_band = st.session_state.get("wallet_band")

if wallet_report and wallet_report.get("summary"):
    summary = wallet_report["summary"]
    first_trade = pd.to_datetime(summary.get("first_trade")) if summary.get("first_trade") else None
    qualifies_cutoff = first_trade is not None and first_trade <= pd.Timestamp("2023-12-31T23:59:59Z")
    badge_text = "OG qualification confirmed" if qualifies_cutoff else "Activity after OG cutoff"
    badge_color = "#22c55e" if qualifies_cutoff else "#f97316"

    wallet_display = st.session_state.get("wallet_address", "").lower()
    if wallet_display:
        wallet_display = wallet_display[:6] + "…" + wallet_display[-4:]

    st.markdown(
        f"""
        <div style="margin-top:1rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:0.6rem;">
            <span style="padding:0.25rem 0.75rem; border-radius:999px; background:{badge_color}; color:#0f172a; font-weight:600;">
                {badge_text}
            </span>
            <span style="color:#475569; font-size:0.95rem;">
                Wallet {wallet_display or 'n/a'} · First trade: {first_trade.strftime('%Y-%m-%d') if first_trade else 'N/A'}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total trades", f"{summary.get('trade_count', 0):,}")
    metric_cols[1].metric("Total volume", f"{summary.get('total_eth', 0):,.2f} ETH")
    metric_cols[2].metric("Platform fees", f"{summary.get('platform_fee_eth', 0):,.2f} ETH")
    metric_cols[3].metric("Royalties", f"{summary.get('royalty_fee_eth', 0):,.2f} ETH")

    if wallet_band:
        cohort_selected = st.session_state.get("cohort_size", 100_000)
        start_pct = wallet_band.get("start_percentile", 0.0)
        end_pct = wallet_band.get("end_percentile", 0.0)
        band_entry = wallet_band.get("bucket_data", {})
        min_band_usd = float(band_entry.get("min_total_usd") or 0.0)
        max_band_usd = float(band_entry.get("max_total_usd") or min_band_usd)
        st.info(
            f"Based on total USD volume, this wallet sits between the top {start_pct:.1f}% and "
            f"{end_pct:.1f}% of the {cohort_selected:,} wallets you’ve defined as the OG cohort. "
            "Adjust the sliders below to explore alternative assumptions."
        )
        with st.expander("Percentile band details", expanded=False):
            st.write(
                f"Band volume range: ${min_band_usd:,.0f} – ${max_band_usd:,.0f} USD"
            )
    else:
        st.warning(
            "Wallet volume falls below your current OG cohort selection. Increase the cohort size or "
            "adjust your definition to include lower-volume wallets."
        )

cohort_estimate = st.session_state.get("cohort_size_estimate")
if cohort_estimate:
    st.caption(
        f"{cohort_selection}: approximately {cohort_estimate:,} wallets qualify under this definition. "
        "Use the cohort size slider below to focus on your own OG definition."
    )

cta_col = st.container()
clicked = False
with cta_col:
    left_spacer, button_area, right_spacer = st.columns([3, 2, 3])
    with button_area:
        clicked = st.button(
            "Estimate my airdrop",
            key="estimate_cta",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.has_revealed_once,
        )

total_supply = TOTAL_SUPPLY

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
        if (
            distribution_rows
            and st.session_state.get("cohort_size_origin") != cohort_selection
        ):
            default_target = snap_value_to_options(
                float(cohort_estimate or slider_mid),
                cohort_slider_options,
            )
            st.session_state["cohort_size"] = int(default_target)
            st.session_state["cohort_size_origin"] = cohort_selection
        current_cohort_value = st.session_state.get("cohort_size", 100_000)
        if current_cohort_value not in cohort_slider_options:
            nearest = min(cohort_slider_options, key=lambda opt: abs(opt - current_cohort_value))
            st.session_state["cohort_size"] = nearest
            current_cohort_value = nearest
        cohort_size = st.select_slider(
            "OG cohort size (wallets)",
            options=cohort_slider_options,
            format_func=lambda val: f"{val:,}",
            label_visibility="collapsed",
            key="cohort_size",
        )

    with top_row[3]:
        st.markdown("**Your percentile band (%)**")
        st.caption("Where you believe you sit within OGs.")
        percentile_options = generate_percentile_options()
        current_tier_value = st.session_state.get("tier_pct", percentile_options[0])
        if current_tier_value not in percentile_options:
            snapped = snap_value_to_options(float(current_tier_value), percentile_options)
            st.session_state["tier_pct"] = snapped
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
