"""Hero and insights rendering for Sea Mom."""

from __future__ import annotations

import html
import textwrap
from dataclasses import dataclass
from typing import List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from app.calculations import format_percentile_option

Step = Tuple[str, str]


@dataclass
class ScenarioSnapshot:
    token_price: float
    wallets_in_tier: int
    og_pool_tokens: float
    featured_share: float
    tier_pct: float
    selected_df: pd.DataFrame
    heatmap_df: pd.DataFrame
    steps: List[Step]


def render_results(
    *,
    scenario_snapshot: ScenarioSnapshot,
    selected_scenario,
    reveal_signature,
) -> None:
    """Render the hero block, insights, stepper, and comparison charts."""

    token_price = scenario_snapshot.token_price
    wallets_in_tier = scenario_snapshot.wallets_in_tier
    og_pool_tokens = scenario_snapshot.og_pool_tokens
    featured_share = scenario_snapshot.featured_share
    selected_df = scenario_snapshot.selected_df
    heatmap_df = scenario_snapshot.heatmap_df
    steps_for_reveal = scenario_snapshot.steps
    tier_pct = scenario_snapshot.tier_pct

    usd_value = selected_scenario.usd_value
    sea_amount = selected_scenario.tokens_per_wallet

    hero_container = st.container()
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
                        <div class='detail'>{html.escape(detail)}</div>
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

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Tier share comparison**")
        st.dataframe(
            selected_df,
            hide_index=True,
            use_container_width=True,
        )
    with col_b:
        st.markdown("**FDV sensitivity heatmap**")
        heatmap_chart = (
            alt.Chart(heatmap_df)
            .mark_rect()
            .encode(
                x=alt.X("FDV ($B):O", title="FDV ($B)"),
                y=alt.Y("Tier Share %:O", title="Tier share of OG pool"),
                color=alt.Color("USD", title="USD per wallet", scale=alt.Scale(scheme="blues")),
                tooltip=["Tier Share %", "FDV ($B)", "Tokens / Wallet", "USD"],
            )
            .properties(height=260)
        )
        st.altair_chart(heatmap_chart, use_container_width=True)

    st.session_state["last_reveal_signature"] = reveal_signature
    st.session_state["has_revealed_once"] = True
