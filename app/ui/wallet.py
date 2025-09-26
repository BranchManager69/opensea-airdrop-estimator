"""Wallet lookup and metrics rendering."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

from app.calculations import determine_percentile_band
from app.config import APP_PUBLIC_BASE, DEMO_WALLET
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
                base_url = (APP_PUBLIC_BASE or "").rstrip("/")
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

        total_eth = float(summary.get("total_eth") or 0.0)
        total_usd = float(summary.get("total_usd") or 0.0)
        platform_fee_eth = float(summary.get("platform_fee_eth") or 0.0)
        royalty_fee_eth = float(summary.get("royalty_fee_eth") or 0.0)
        platform_fee_usd = float(summary.get("platform_fee_usd") or 0.0)
        royalty_fee_usd = float(summary.get("royalty_fee_usd") or 0.0)

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

        fee_rows = []
        if platform_fee_eth or platform_fee_usd:
            fee_rows.append(
                {
                    "Type": "Platform",
                    "ETH": platform_fee_eth,
                    "USD": platform_fee_usd,
                    "ETH %": (platform_fee_eth / total_eth * 100) if total_eth else 0.0,
                    "USD %": (platform_fee_usd / total_usd * 100) if total_usd else 0.0,
                }
            )
        if royalty_fee_eth or royalty_fee_usd:
            fee_rows.append(
                {
                    "Type": "Royalties",
                    "ETH": royalty_fee_eth,
                    "USD": royalty_fee_usd,
                    "ETH %": (royalty_fee_eth / total_eth * 100) if total_eth else 0.0,
                    "USD %": (royalty_fee_usd / total_usd * 100) if total_usd else 0.0,
                }
            )

        net_eth = max(total_eth - platform_fee_eth - royalty_fee_eth, 0.0)
        net_usd = max(total_usd - platform_fee_usd - royalty_fee_usd, 0.0)
        if total_eth or total_usd:
            fee_rows.append(
                {
                    "Type": "Net to trader",
                    "ETH": net_eth,
                    "USD": net_usd,
                    "ETH %": (net_eth / total_eth * 100) if total_eth else 0.0,
                    "USD %": (net_usd / total_usd * 100) if total_usd else 0.0,
                }
            )

        if fee_rows:
            fee_df = pd.DataFrame(fee_rows)
            for column, places in [("ETH", 3), ("USD", 2), ("ETH %", 2), ("USD %", 2)]:
                fee_df[column] = fee_df[column].round(places)
            fee_df.rename(columns={"ETH": "ETH", "USD": "USD", "ETH %": "% of ETH", "USD %": "% of USD"}, inplace=True)

            formatted_fee_df = fee_df.copy()
            formatted_fee_df["ETH"] = formatted_fee_df["ETH"].map(lambda v: f"Ξ{v:,.3f}")
            formatted_fee_df["USD"] = formatted_fee_df["USD"].map(lambda v: f"${v:,.2f}")
            formatted_fee_df["% of ETH"] = formatted_fee_df["% of ETH"].map(lambda v: f"{v:,.2f}%")
            formatted_fee_df["% of USD"] = formatted_fee_df["% of USD"].map(lambda v: f"{v:,.2f}%")

            st.markdown("**Fee profile**")
            st.dataframe(
                formatted_fee_df,
                use_container_width=True,
                hide_index=True,
            )

        collection_rows = wallet_report.get("collections") or []
        if collection_rows:
            collections_df = pd.DataFrame(collection_rows)
            if not collections_df.empty:
                collections_df = collections_df.copy()
                collections_df["total_usd"] = collections_df["total_usd"].astype(float)
                collections_df["total_eth"] = collections_df["total_eth"].astype(float)
                collections_df.sort_values("total_usd", ascending=False, inplace=True)
                if total_usd:
                    collections_df["share_usd_pct"] = (collections_df["total_usd"] / total_usd * 100).round(2)
                else:
                    collections_df["share_usd_pct"] = 0.0

                collections_df = collections_df.rename(
                    columns={
                        "collection": "Collection",
                        "trade_count": "Trades",
                        "total_eth": "ETH",
                        "total_usd": "USD",
                        "share_usd_pct": "% of USD",
                    }
                )

                display_df = collections_df[["Collection", "Trades", "ETH", "USD", "% of USD"]].copy()
                display_df["ETH"] = display_df["ETH"].map(lambda v: f"Ξ{v:,.3f}")
                display_df["USD"] = display_df["USD"].map(lambda v: f"${v:,.2f}")
                display_df["% of USD"] = display_df["% of USD"].map(lambda v: f"{v:,.2f}%")

                st.markdown("**Collection mix**")
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                )

    return wallet_report, wallet_band
