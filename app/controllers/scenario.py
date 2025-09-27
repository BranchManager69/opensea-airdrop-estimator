"""Scenario assembly helpers for the Sea Mom dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from app.calculations import (
    ScenarioResult,
    build_heatmap_data,
    build_share_table,
    compute_scenario,
    determine_percentile_band,
    format_percentile_option,
)
from app.config import TOTAL_SUPPLY
from app.ui.cohort import LoadedCohort
from app.ui.results import ScenarioSnapshot, Step


@dataclass
class ScenarioBuildResult:
    """Container for all scenario artefacts required by the Streamlit page."""

    scenario_cards: List[Dict[str, Any]]
    scenario_snapshot: ScenarioSnapshot
    scenario_bands: Dict[str, Dict[str, Any]]
    curve_rows: List[Dict[str, Any]]
    primary_result: ScenarioResult
    primary_label: str
    primary_cohort_wallets: int
    steps_for_reveal: List[Step]
    current_signature: Tuple[Any, ...]
    featured_share: float
    token_price: float
    total_usd_snapshot: float


def _compute_token_price(fdv_billion: float, total_supply: int) -> float:
    return (fdv_billion * 1_000_000_000) / total_supply


def build_scenario_context(
    *,
    cohorts: Dict[str, LoadedCohort],
    primary_name: str,
    cohort_size: int,
    tier_pct: float,
    og_pool_pct: float,
    fdv_billion: float,
    share_options: Sequence[float],
    fdv_sensitivity: Iterable[float],
    wallet_report: Optional[Dict[str, Any]],
    total_supply: int = TOTAL_SUPPLY,
) -> ScenarioBuildResult:
    """Return all artefacts required to render the scenario section."""

    primary_cohort = cohorts[primary_name]
    baseline_rows = primary_cohort.rows

    total_usd_snapshot = 0.0
    if wallet_report and baseline_rows:
        summary_snapshot = wallet_report.get("summary", {}) or {}
        total_usd_snapshot = float(summary_snapshot.get("total_usd") or 0.0)

    if not share_options:
        share_options = [20, 30, 40]
    featured_share = share_options[0]

    token_price = _compute_token_price(fdv_billion, total_supply)

    scenario_cards: List[Dict[str, Any]] = []
    scenario_bands: Dict[str, Dict[str, Any]] = {}
    curve_rows: List[Dict[str, Any]] = []
    primary_result: Optional[ScenarioResult] = None
    primary_label = primary_cohort.config.get("title", primary_name)
    primary_cohort_wallets = cohort_size

    base_estimate = primary_cohort.estimate or cohort_size or 1
    if base_estimate <= 0:
        base_estimate = max(cohort_size, 1)

    for name, data in cohorts.items():
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

        wallets_in_tier_value = max(1, int(round(scenario_cohort_size * (tier_pct / 100))))

        band_text = ""
        band_mid = None
        start_pct = None
        end_pct = None
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
        subtitle = " · ".join([bit for bit in subtitle_bits if bit]) or data.name

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

        card_curve_points: List[Dict[str, Any]] = []
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
            primary_cohort_wallets = scenario_cohort_size
            if full_label:
                primary_label = full_label

    if primary_result is None:
        primary_result = compute_scenario(
            total_supply=total_supply,
            og_pool_pct=og_pool_pct,
            fdv_billion=fdv_billion,
            cohort_size=cohort_size,
            tier_pct=tier_pct,
            share_pct=featured_share,
        )

    primary_wallets_in_tier = max(1, int(round(primary_cohort_wallets * (tier_pct / 100))))

    steps_for_reveal: List[Step] = [
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

    return ScenarioBuildResult(
        scenario_cards=scenario_cards,
        scenario_snapshot=scenario_snapshot,
        scenario_bands=scenario_bands,
        curve_rows=curve_rows,
        primary_result=primary_result,
        primary_label=primary_label,
        primary_cohort_wallets=primary_cohort_wallets,
        steps_for_reveal=steps_for_reveal,
        current_signature=current_signature,
        featured_share=featured_share,
        token_price=token_price,
        total_usd_snapshot=total_usd_snapshot,
    )
