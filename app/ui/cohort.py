"""Cohort data helpers and scenario rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import textwrap

import streamlit as st

from app.calculations import (
    generate_cohort_slider_options,
    round_to_step,
    round_up_to_step,
)
from app.config import COHORT_CONFIG
from app.data_sources import estimate_og_cohort_size, load_distribution


@dataclass
class LoadedCohort:
    """Loaded distribution and metadata for a cohort scenario."""

    name: str
    rows: List[Dict[str, Any]]
    estimate: int
    config: Dict[str, Any]


def load_cohort_data() -> Dict[str, LoadedCohort]:
    """Load every cohort distribution defined in ``COHORT_CONFIG``."""

    cohorts: Dict[str, LoadedCohort] = {}
    for display_name, config in COHORT_CONFIG.items():
        rows = load_distribution(config["path"])
        estimate = estimate_og_cohort_size(rows)
        cohorts[display_name] = LoadedCohort(
            name=display_name,
            rows=rows,
            estimate=estimate,
            config=config,
        )
    return cohorts


def build_slider_defaults(cohort: LoadedCohort) -> tuple[List[int], int]:
    """Return slider options and a midpoint anchored to a cohort estimate."""

    slider_min = 50_000
    slider_mid = 100_000
    slider_max = 500_000

    if cohort.estimate:
        slider_mid = round_to_step(max(slider_min, cohort.estimate), 5_000)
        slider_max = max(slider_max, round_up_to_step(cohort.estimate * 1.2, 5_000))
        slider_mid = min(slider_max, slider_mid)

    slider_options = generate_cohort_slider_options(
        min_val=slider_min,
        mid_val=slider_mid,
        max_val=slider_max,
    )

    return slider_options, slider_mid


def render_scenario_cards(scenarios: Sequence[Dict[str, Any]]) -> None:
    """Render static scenario cards summarising each cohort."""

    if not scenarios:
        return

    cards_html: List[str] = []
    for scenario in scenarios:
        payout_text = scenario.get("payout_text", "")
        tokens_text = scenario.get("tokens_text", "")
        wallets_text = scenario.get("wallets_text", "")
        band_text = scenario.get("band_text") or ""
        cards_html.append(
            textwrap.dedent(
                f"""
                <div class='cohort-card scenario-card'>
                    <span class='cohort-card-title'>{scenario['title']}</span>
                    <span class='cohort-card-year'>{scenario['subtitle']}</span>
                    <div class='scenario-card-metric'>{payout_text}</div>
                    <div class='scenario-card-submetric'>{tokens_text}</div>
                    <div class='scenario-card-foot'>{wallets_text}</div>
                    {f"<div class='scenario-card-foot subtle'>{band_text}</div>" if band_text else ''}
                </div>
                """
            ).strip()
        )

    st.markdown(
        "<div class='cohort-cards-row scenario-cards'>" + "".join(cards_html) + "</div>",
        unsafe_allow_html=True,
    )
