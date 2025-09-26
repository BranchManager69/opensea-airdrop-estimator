"""Wallet lookup and metrics rendering."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

from app.calculations import determine_percentile_band
from app.config import DEMO_WALLET
from app.data_sources import estimate_og_cohort_size, fetch_wallet_report


def render_wallet_section(
    *,
    distribution_rows: List[Dict[str, Any]],
    preset_wallet: Optional[str] = None,
    auto_fetch: bool = False,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Render wallet lookup controls and summary metrics."""

    wallet_holder = st.container()

    def perform_fetch(address: str) -> None:
        address = address.strip()
        if not address:
            return
        try:
            with st.spinner("Contacting Dune …"):
                report = fetch_wallet_report(address)
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
                if distribution_rows:
                    cohort_est = estimate_og_cohort_size(distribution_rows)
                    if cohort_est:
                        st.session_state["cohort_size_estimate"] = cohort_est
                st.session_state["wallet_address"] = address
                st.success("Wallet snapshot updated. Scroll down to view personalised metrics.")
        except RuntimeError as err:
            st.error(str(err))
        except requests.exceptions.RequestException as err:
            st.error(f"Failed to fetch wallet data: {err}")

    if preset_wallet:
        st.session_state["wallet_input"] = preset_wallet

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
        with fetch_cols[1]:
            share_clicked = st.button(
                "Copy share link",
                type="primary",
                disabled=not wallet_address.strip(),
            )

        if fetch_clicked:
            if not wallet_address:
                st.warning("Enter a wallet address to fetch OpenSea activity.")
            else:
                perform_fetch(wallet_address)
                st.session_state["_autofetched_wallet"] = wallet_address.lower()

        if share_clicked:
            normalized = wallet_address.strip()
            if not normalized:
                st.warning("Enter a wallet address before copying a share link.")
            else:
                base_url = st.secrets.get("BASE_URL", "").rstrip("/")
                share_url = f"{base_url}/?wallet={normalized}" if base_url else f"/?wallet={normalized}"
                st.session_state["_share_url"] = share_url
                escaped = share_url.replace("'", "\'")
                st.markdown(
                    f"<script>navigator.clipboard.writeText('{escaped}');</script>",
                    unsafe_allow_html=True,
                )
                st.toast("Share link copied to clipboard.")
                st.query_params["wallet"] = normalized

    if auto_fetch and preset_wallet:
        normalized = preset_wallet.lower()
        if st.session_state.get("_autofetched_wallet") != normalized:
            perform_fetch(preset_wallet)
            st.session_state["_autofetched_wallet"] = normalized

    share_url_value = st.session_state.get("_share_url")
    if share_url_value:
        st.caption(f"Share URL ready: {share_url_value}")

    wallet_report = st.session_state.get("wallet_report")
    wallet_band = st.session_state.get("wallet_band")

    if wallet_report and wallet_report.get("summary"):
        summary = wallet_report["summary"]
        first_trade = (
            pd.to_datetime(summary.get("first_trade")) if summary.get("first_trade") else None
        )
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

    return wallet_report, wallet_band
