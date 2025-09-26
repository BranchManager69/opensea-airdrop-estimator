"""Cohort selection timeline and related helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import streamlit as st

from app.calculations import (
    generate_cohort_slider_options,
    round_to_step,
    round_up_to_step,
)
from app.config import COHORT_CONFIG
from app.data_sources import estimate_og_cohort_size, load_distribution


@dataclass
class CohortContext:
    """Snapshot of the active cohort configuration."""

    selection: str
    distribution_rows: List[Dict[str, Any]]
    estimate: int
    slider_options: List[int]
    slider_mid: int


def render_cohort_selector() -> CohortContext:
    """Render cohort cards and return context needed for downstream controls."""

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

    cohort_distributions: Dict[str, List[Dict[str, Any]]] = {}
    cohort_totals: Dict[str, int] = {}
    for name in cohort_names:
        rows = load_distribution(COHORT_CONFIG[name]["path"])
        cohort_distributions[name] = rows
        cohort_totals[name] = estimate_og_cohort_size(rows)

    timeline_container = st.container()
    with timeline_container:
        st.markdown("<div class='cohort-timeline'>", unsafe_allow_html=True)
        cards_html: List[str] = []
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
    existing_slug = st.query_params.get("cohort")
    if isinstance(existing_slug, (list, tuple)):
        existing_slug = existing_slug[0] if existing_slug else None
    if existing_slug != current_slug:
        st.query_params["cohort"] = current_slug

    distribution_rows = cohort_distributions.get(cohort_selection, [])
    if not distribution_rows:
        st.warning(
            f"Percentile distribution file missing for {cohort_selection}. "
            f"Expected at {COHORT_CONFIG[cohort_selection]['path']}"
        )

    cohort_estimate = cohort_totals.get(cohort_selection, 0)
    if distribution_rows:
        st.session_state["cohort_size_estimate"] = cohort_estimate
    else:
        cohort_estimate = st.session_state.get("cohort_size_estimate", 0)

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

    slider_options = generate_cohort_slider_options(
        min_val=slider_min,
        mid_val=slider_mid,
        max_val=slider_max,
    )

    return CohortContext(
        selection=cohort_selection,
        distribution_rows=distribution_rows,
        estimate=cohort_estimate,
        slider_options=slider_options,
        slider_mid=slider_mid,
    )
