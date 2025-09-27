"""Share card UI elements."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import streamlit as st

from app.calculations import format_percentile_option
from app.share_service import ShareServiceError, create_share_card

ShareCardKey = Tuple[Any, ...]


def _format_wallet(address: str | None) -> str:
    if not address:
        return ""
    value = address.strip()
    if len(value) <= 12:
        return value
    return value[:6] + "…" + value[-4:]


def render_share_panel(
    *,
    current_signature: ShareCardKey,
    cohort_label: str,
    cohort_wallets: int,
    og_pool_pct: float,
    fdv_billion: float,
    tier_pct: float,
    featured_share: float,
    token_price: float,
    scenario_usd: float,
    scenario_tokens: float,
    wallet_report: Dict[str, Any] | None,
) -> None:
    """Render the share-card controls below the results section."""

    st.markdown("""
        <div class='share-panel'>
            <h3>Flex your Sea Mom projection</h3>
            <p>Generate a shareable card with today's assumptions and wallet history.</p>
        </div>
    """, unsafe_allow_html=True)

    wallet_address = st.session_state.get("wallet_address")
    if not wallet_address or not wallet_report or not wallet_report.get("summary"):
        st.info("Fetch a wallet history above before generating a share card.")
        return

    last_signature = st.session_state.get("last_reveal_signature")
    if last_signature != current_signature:
        st.warning("Update the estimate above and click **Estimate my airdrop** before sharing.")
        return

    share_cache: Dict[ShareCardKey, Dict[str, Any]] = st.session_state.setdefault("share_card_cache", {})
    existing_card = share_cache.get(current_signature)

    summary = wallet_report.get("summary", {})
    trade_count = int(float(summary.get("trade_count") or 0))
    total_eth = float(summary.get("total_eth") or 0.0)
    total_usd = float(summary.get("total_usd") or 0.0)
    last_trade = summary.get("last_trade") or summary.get("last_activity")

    percentile_label = format_percentile_option(tier_pct)

    with st.container():
        cols = st.columns([2, 3])
        with cols[0]:
            st.markdown(
                f"**Wallet**: {_format_wallet(wallet_address)}  \
**Volume**: {total_eth:,.2f} ETH ({total_usd:,.0f} USD)"
            )
            cohort_context_text = cohort_label
            if cohort_wallets:
                cohort_context_text += f" · {cohort_wallets:,} wallets"
            st.markdown(f"**Cohort**: {cohort_context_text}")
            st.markdown(f"**Tier**: {percentile_label} · {featured_share:.0f}% OG pool")

            if existing_card:
                share_url = existing_card.get("share_url")
                st.success("Share card ready!")
                if share_url:
                    st.markdown(f"[View share page]({share_url})")
                    st.caption(f"Share link: {share_url}")
                    if st.button("Copy share link", type="primary", key="copy-share-link"):
                        escaped = share_url.replace("'", "\'")
                        st.markdown(
                            f"<script>navigator.clipboard.writeText('{escaped}');</script>",
                            unsafe_allow_html=True,
                        )
                        st.toast("Share link copied.")
            else:
                if st.button("Generate Sea Mom Flex", type="primary"):
                    payload = {
                        "wallet": wallet_address,
                        "payoutUsd": float(scenario_usd),
                        "payoutTokens": float(scenario_tokens),
                        "tokenPrice": float(token_price),
                        "cohortLabel": cohort_label,
                        "cohortWallets": int(cohort_wallets or 0),
                        "percentileLabel": percentile_label,
                        "sharePct": float(featured_share),
                        "fdvBillion": float(fdv_billion),
                        "ogPoolPct": float(og_pool_pct),
                        "tradeCount": trade_count,
                        "totalEth": total_eth,
                        "totalUsd": total_usd,
                        "asOf": last_trade,
                    }
                    try:
                        with st.spinner("Rendering your card…"):
                            card = create_share_card(payload)
                    except ShareServiceError as err:
                        st.error(str(err))
                    else:
                        share_cache[current_signature] = card
                        st.session_state["share_card_cache"] = share_cache
                        st.session_state["share_card_last_id"] = card.get("id")
                        st.toast("Share card generated!")
                        existing_card = card

        with cols[1]:
            if existing_card and existing_card.get("image_url"):
                st.image(existing_card["image_url"], caption="Share preview", use_container_width=True)
            else:
                st.warning("Generating share preview…")

    st.divider()
