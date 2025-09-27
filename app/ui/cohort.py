"""Cohort data helpers and scenario rendering."""

from __future__ import annotations

import math
from urllib.parse import quote
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


def _build_sparkline(points: Sequence[Dict[str, Any]], highlight_pct: float | None, highlight_usd: float | None) -> str:
    """Return an inline SVG sparkline for scenario percentile curves."""

    if not points:
        return ""

    filtered: List[Dict[str, float]] = []
    for point in points:
        try:
            percentile = float(point.get("percentile", 0.0))
            usd_value = float(point.get("usd", 0.0))
        except (TypeError, ValueError):
            continue
        if percentile <= 0 or usd_value <= 0:
            continue
        filtered.append({"percentile": percentile, "usd": usd_value})

    if len(filtered) < 2:
        return ""

    filtered.sort(key=lambda item: item["percentile"])

    width = 220.0
    height = 64.0

    min_pct = filtered[0]["percentile"]
    max_pct = filtered[-1]["percentile"]
    if math.isclose(max_pct, min_pct):
        max_pct = min_pct + 1.0

    usd_values = [item["usd"] for item in filtered if item["usd"] > 0]
    if not usd_values:
        return ""

    log_values = [math.log10(value) for value in usd_values if value > 0]
    min_log = min(log_values)
    max_log = max(log_values)
    if math.isclose(max_log, min_log):
        max_log = min_log + 1.0

    def scale_x(percentile: float) -> float:
        return (percentile - min_pct) / (max_pct - min_pct) * width

    def scale_y(usd: float) -> float:
        target = math.log10(usd) if usd > 0 else min_log
        position = (target - min_log) / (max_log - min_log)
        return height - (position * height)

    path_segments: List[str] = []
    fill_segments: List[str] = [f"M0,{height:.2f}"]

    for idx, item in enumerate(filtered):
        x = scale_x(item["percentile"])
        y = scale_y(item["usd"])
        command = "M" if idx == 0 else "L"
        path_segments.append(f"{command}{x:.2f},{y:.2f}")
        fill_segments.append(f"L{x:.2f},{y:.2f}")

    last_x = scale_x(filtered[-1]["percentile"])
    fill_segments.append(f"L{last_x:.2f},{height:.2f} Z")

    path_d = " ".join(path_segments)
    fill_d = " ".join(fill_segments)

    highlight_markup = ""
    if highlight_pct is not None and highlight_usd and highlight_usd > 0:
        highlight_x = scale_x(highlight_pct)
        highlight_y = scale_y(highlight_usd)
        highlight_markup = (
            f"<circle cx='{highlight_x:.2f}' cy='{highlight_y:.2f}' r='4.5' fill='#2081E2' "
            "stroke='white' stroke-width='1.5'/>"
        )

    svg_markup = (
        "<svg class='scenario-card-sparkline-svg' viewBox='0 0 220 64' "
        "preserveAspectRatio='none'>"
        "<defs>"
        "<linearGradient id='sparklineGradient' x1='0%' y1='0%' x2='0%' y2='100%'>"
        "<stop offset='0%' stop-color='rgba(32,129,226,0.28)'/>"
        "<stop offset='100%' stop-color='rgba(32,129,226,0.02)'/>"
        "</linearGradient>"
        "</defs>"
        f"<path d='{fill_d}' fill='url(#sparklineGradient)' stroke='none'/>"
        f"<path d='{path_d}' fill='none' stroke='#2081E2' stroke-width='2.2' stroke-linejoin='round'/>"
        f"{highlight_markup}"
        "</svg>"
    )

    encoded = quote(svg_markup)
    return (
        "<img src=\"data:image/svg+xml;utf8," + encoded +
        "\" class='scenario-card-sparkline-svg' alt='Percentile distribution sparkline'/>"
    )


def render_scenario_cards(
    scenarios: Sequence[Dict[str, Any]],
    *,
    slider_options: Sequence[int],
) -> None:
    """Render scenario cards with inline trendlines and the cohort slider."""

    if not scenarios:
        return

    st.markdown(
        """
        <div class='scenario-strip'>
            <div class='scenario-strip-header'>How does your allocation shift as the OG pool moves?</div>
            <p class='scenario-strip-lead'>Each card re-computes from the same assumptions above. Adjust the cohort size slider to tune all three in lockstep.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cards_html: List[str] = []
    for scenario in scenarios:
        payout_text = scenario.get("payout_text", "")
        tokens_text = scenario.get("tokens_text", "")
        wallets_text = scenario.get("wallets_text", "")
        band_text = scenario.get("band_text") or ""
        sparkline_svg = _build_sparkline(
            scenario.get("curve_points") or [],
            scenario.get("highlight_mid"),
            scenario.get("highlight_usd"),
        )
        selected_class = " selected" if scenario.get("is_primary") else ""
        cards_html.append(
            textwrap.dedent(
                f"""
                <div class='cohort-card scenario-card{selected_class}'>
                    <span class='cohort-card-title'>{scenario['title']}</span>
                    <span class='cohort-card-year'>{scenario['subtitle']}</span>
                    <div class='scenario-card-metric'>{payout_text}</div>
                    <div class='scenario-card-submetric'>{tokens_text}</div>
                    <div class='scenario-card-foot'>{wallets_text}</div>
                    {f"<div class='scenario-card-foot subtle'>{band_text}</div>" if band_text else ''}
                    {f"<div class='scenario-card-sparkline'>{sparkline_svg}</div>" if sparkline_svg else ''}
                </div>
                """
            ).strip()
        )

    st.markdown(
        "<div class='cohort-cards-row scenario-cards'>" + "".join(cards_html) + "</div>",
        unsafe_allow_html=True,
    )

    if slider_options:
        current_value = st.session_state.get("cohort_size")
        if current_value not in slider_options:
            current_value = slider_options[len(slider_options) // 2]
        st.markdown("<div class='scenario-slider-label'>Scenario cohort size</div>", unsafe_allow_html=True)
        st.select_slider(
            "Scenario cohort size",
            options=slider_options,
            format_func=lambda val: f"{val:,}",
            key="cohort_size",
            value=current_value,
            label_visibility="collapsed",
        )
        st.caption("Updates all cohort scenarios simultaneously.")
