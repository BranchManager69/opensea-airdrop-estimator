"""Share card flow coordination for Sea Mom."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import streamlit as st

from app.calculations import ScenarioResult, format_percentile_option
from app.share_service import ShareServiceError
from app.ui.share import ShareCardKey, ensure_share_card


@dataclass
class SharePrefetchResult:
    """Outcome of attempting to pre-generate the share card."""

    card: Optional[Dict[str, Any]]
    payload: Optional[Dict[str, Any]]
    warning: Optional[str] = None


def _build_payload(
    *,
    wallet_report: Dict[str, Any],
    wallet_address: str,
    scenario_result: ScenarioResult,
    tier_pct: float,
    primary_label: str,
    primary_cohort_wallets: int,
    featured_share: float,
    fdv_billion: float,
    og_pool_pct: float,
    token_price: float,
) -> Dict[str, Any]:
    summary = wallet_report.get("summary", {})
    trade_count = int(float(summary.get("trade_count") or 0))
    total_eth = float(summary.get("total_eth") or 0.0)
    total_usd = float(summary.get("total_usd") or 0.0)
    last_trade = summary.get("last_trade") or summary.get("last_activity")

    percentile_label = format_percentile_option(tier_pct)

    payload: Dict[str, Any] = {
        "wallet": wallet_address,
        "payoutUsd": float(scenario_result.usd_value),
        "payoutTokens": float(scenario_result.tokens_per_wallet),
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
    return payload


def prefetch_share_card(
    *,
    wallet_report: Optional[Dict[str, Any]],
    wallet_address: Optional[str],
    scenario_result: ScenarioResult,
    tier_pct: float,
    primary_label: str,
    primary_cohort_wallets: int,
    featured_share: float,
    fdv_billion: float,
    og_pool_pct: float,
    token_price: float,
    current_signature: ShareCardKey,
) -> SharePrefetchResult:
    """Generate (or load) the share card ahead of rendering the share panel."""

    if not wallet_address or not wallet_report or not wallet_report.get("summary"):
        return SharePrefetchResult(card=None, payload=None)

    payload = _build_payload(
        wallet_report=wallet_report,
        wallet_address=wallet_address,
        scenario_result=scenario_result,
        tier_pct=tier_pct,
        primary_label=primary_label,
        primary_cohort_wallets=primary_cohort_wallets,
        featured_share=featured_share,
        fdv_billion=fdv_billion,
        og_pool_pct=og_pool_pct,
        token_price=token_price,
    )

    try:
        card = ensure_share_card(
            signature=current_signature,
            payload=payload,
            show_spinner=False,
        )
    except ShareServiceError as err:
        st.warning(f"Share preview unavailable: {err}")
        return SharePrefetchResult(card=None, payload=payload, warning=str(err))

    return SharePrefetchResult(card=card, payload=payload)
