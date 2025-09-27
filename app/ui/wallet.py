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
                    new_percentile = float(max(0.1, min(100.0, mid_percentile)))
                    st.session_state["tier_pct"] = new_percentile
                    st.session_state["tier_pct_source"] = {
                        "value": new_percentile,
                        "from_wallet": True,
                    }
                    st.session_state["tier_pct_manual"] = False
                else:
                    st.info(
                        "This wallet’s volume falls outside the cohort size you selected. "
                        "Increase the cohort or adjust the OG definition to include it."
                    )
                    st.session_state["tier_pct_source"] = {
                        "value": st.session_state.get("tier_pct"),
                        "from_wallet": False,
                    }
                if distribution_rows:
                    cohort_est = estimate_og_cohort_size(distribution_rows)
                    if cohort_est:
                        st.session_state["cohort_size_estimate"] = cohort_est
                st.session_state["wallet_address"] = address
                st.query_params["wallet"] = address
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
        fetch_clicked = st.button("Fetch history", type="secondary")

        if fetch_clicked:
            if not wallet_address:
                st.warning("Enter a wallet address to fetch OpenSea activity.")
            else:
                perform_fetch(wallet_address)
                st.session_state["_autofetched_wallet"] = wallet_address.lower()

    if auto_fetch and preset_wallet:
        normalized = preset_wallet.lower()
        if st.session_state.get("_autofetched_wallet") != normalized:
            perform_fetch(preset_wallet)
            st.session_state["_autofetched_wallet"] = normalized

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

        bands_summary = st.session_state.get("scenario_bands") or {}
        if bands_summary:
            st.markdown("**Percentile placement across cohorts**")
            bullet_lines = []
            for info in bands_summary.values():
                label = info.get("label") or "Unnamed cohort"
                start_pct = info.get("start")
                end_pct = info.get("end")
                cohort_sz = info.get("cohort_size")
                if start_pct is not None and end_pct is not None:
                    cohort_text = f" of {cohort_sz:,} wallets" if cohort_sz else ""
                    bullet_lines.append(
                        f"- **{label}** · top {start_pct:.1f}% – {end_pct:.1f}%{cohort_text}"
                    )
                else:
                    bullet_lines.append(
                        f"- **{label}** · below the modeled volume range"
                    )
            st.markdown("\n".join(bullet_lines))
        elif wallet_report and wallet_report.get("summary"):
            st.info("Run the estimate above to map percentile placement across cohorts.")

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

            platform_pct = (platform_fee_usd / total_usd * 100) if total_usd else 0.0
            royalty_pct = (royalty_fee_usd / total_usd * 100) if total_usd else 0.0
            net_pct_display = max(0.0, 100.0 - platform_pct - royalty_pct)

            fee_highlight = f"""
                <div class='fee-highlight'>
                    <div class='fee-highlight-title'>Fee profile</div>
                    <div class='fee-highlight-grid'>
                        <div class='fee-highlight-item'>
                            <span class='label'>Platform</span>
                            <span class='value'>{platform_pct:,.1f}%</span>
                            <span class='hint'>≈ ${platform_fee_usd:,.0f}</span>
                        </div>
                        <div class='fee-highlight-item'>
                            <span class='label'>Royalties</span>
                            <span class='value'>{royalty_pct:,.1f}%</span>
                            <span class='hint'>≈ ${royalty_fee_usd:,.0f}</span>
                        </div>
                        <div class='fee-highlight-item'>
                            <span class='label'>Net to trader</span>
                            <span class='value'>{net_pct_display:,.1f}%</span>
                            <span class='hint'>≈ ${net_usd:,.0f}</span>
                        </div>
                    </div>
                </div>
            """
            st.markdown(fee_highlight, unsafe_allow_html=True)
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
                if "collection" not in collections_df.columns:
                    collections_df["collection"] = collections_df.get("label")
                else:
                    collections_df["collection"] = collections_df["collection"].fillna(collections_df.get("label"))
                for candidate in ["collection_name", "collection_slug", "project", "project_slug", "name"]:
                    if candidate in collections_df.columns:
                        collections_df["collection"] = collections_df["collection"].fillna(collections_df[candidate])
                collections_df["total_usd"] = collections_df.get("total_usd", 0).astype(float)
                collections_df["total_eth"] = collections_df.get("total_eth", 0).astype(float)
                if "trade_count" not in collections_df.columns:
                    collections_df["trade_count"] = collections_df.get("trade_count", 0)
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
                display_cols = [c for c in ["Collection", "Trades", "ETH", "USD", "% of USD"] if c in collections_df.columns]
                if display_cols:
                    display_df = collections_df[display_cols].copy()
                    if "Collection" in display_df.columns:
                        if "collection_slug" in collections_df.columns:
                            display_df["Collection"] = display_df["Collection"].fillna(collections_df["collection_slug"])
                        display_df["Collection"] = display_df["Collection"].fillna("Unknown collection")
                    if "ETH" in display_df.columns:
                        display_df["ETH"] = display_df["ETH"].map(lambda v: f"Ξ{v:,.3f}")
                    if "USD" in display_df.columns:
                        display_df["USD"] = display_df["USD"].map(lambda v: f"${v:,.2f}")
                    if "% of USD" in display_df.columns:
                        display_df["% of USD"] = display_df["% of USD"].map(lambda v: f"{v:,.2f}%")

                    st.markdown("**Collection mix**")
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                    )

    return wallet_report, wallet_band
