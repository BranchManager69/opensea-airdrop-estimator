"""Main Streamlit entrypoint for the Sea Mom airdrop estimator."""

from __future__ import annotations

import textwrap
from typing import Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from app.calculations import determine_percentile_band
from app.config import DEFAULT_REVEAL_DURATION, TOTAL_SUPPLY, resolve_page_icon
from app.controllers import build_scenario_context, prefetch_share_card
from app.state import bootstrap_session_state
from app.ui.cohort import build_slider_defaults, load_cohort_data, render_scenario_cards
from app.ui.inputs import render_input_panel
from app.ui.layout import inject_global_styles, render_header
from app.ui.reveal import run_reveal_presentation
from app.ui.results import render_results
from app.ui.share import render_share_panel
from app.ui.wallet import render_wallet_section


def _resolve_wallet_param() -> str | None:
    params = st.query_params
    wallet_values = params.get("wallet")
    if isinstance(wallet_values, (list, tuple)):
        wallet_param = wallet_values[0] if wallet_values else None
    else:
        wallet_param = wallet_values
    return wallet_param.strip() if wallet_param else None


def main() -> None:
    st.set_page_config(
        page_title="Sea Mom",
        page_icon=resolve_page_icon(),
        layout="wide",
    )

    bootstrap_session_state()

    wallet_param = _resolve_wallet_param()

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

    total_supply = TOTAL_SUPPLY

    if wallet_report and baseline_rows:
        summary_snapshot = wallet_report.get("summary", {}) or {}
        total_usd_baseline = float(summary_snapshot.get("total_usd") or 0.0)
        recomputed_band = determine_percentile_band(
            total_usd_baseline,
            baseline_rows,
            cohort_size,
        )
        st.session_state["wallet_band"] = recomputed_band
        wallet_band = recomputed_band

    scenario_context = build_scenario_context(
        cohorts=cohort_data,
        primary_name=primary_name,
        cohort_size=cohort_size,
        tier_pct=tier_pct,
        og_pool_pct=og_pool_pct,
        fdv_billion=fdv_billion,
        share_options=share_options,
        fdv_sensitivity=fdv_sensitivity,
        wallet_report=wallet_report,
        total_supply=total_supply,
    )

    scenario_cards = scenario_context.scenario_cards
    scenario_snapshot = scenario_context.scenario_snapshot
    primary_result = scenario_context.primary_result
    primary_label = scenario_context.primary_label
    primary_cohort_wallets = scenario_context.primary_cohort_wallets
    current_signature = scenario_context.current_signature
    featured_share = scenario_context.featured_share
    token_price = scenario_context.token_price
    total_usd_snapshot = scenario_context.total_usd_snapshot
    steps_for_reveal = scenario_snapshot.steps

    st.session_state["scenario_bands"] = scenario_context.scenario_bands
    st.session_state["scenario_curves"] = scenario_context.curve_rows

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

        wallet_address = st.session_state.get("wallet_address")
        prefetch_result = prefetch_share_card(
            wallet_report=wallet_report,
            wallet_address=wallet_address,
            scenario_result=primary_result,
            tier_pct=tier_pct,
            primary_label=primary_label,
            primary_cohort_wallets=primary_cohort_wallets,
            featured_share=featured_share,
            fdv_billion=fdv_billion,
            og_pool_pct=og_pool_pct,
            token_price=token_price,
            current_signature=current_signature,
        )

        primary_band_info = scenario_context.scenario_bands.get(primary_name, {})
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

        preview_card = prefetch_result.card or st.session_state.get("share_card_cache", {}).get(current_signature)
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
                precomputed_card=prefetch_result.card,
                payload=prefetch_result.payload,
            )

        with st.expander("Wallet breakdown", expanded=False):
            render_wallet_breakdown(wallet_report, wallet_band)

        with st.expander("Scenario comparisons", expanded=True):
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


if __name__ == "__main__":
    main()
