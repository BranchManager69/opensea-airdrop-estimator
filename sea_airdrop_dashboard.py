import html
import json
import math
import os
from typing import Any, Dict, List
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from dotenv import load_dotenv

import altair as alt
import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="SEA Airdrop Estimator",
    layout="wide",
)

load_dotenv()
DATA_DIR = Path("data")
DUNE_QUERY_WALLET_STATS_ID = 5850749

COHORT_CONFIG: Dict[str, Dict[str, Any]] = {
    "Super OG (≤2021)": {
        "slug": "super_og",
        "path": DATA_DIR / "opensea_og_percentile_distribution_pre2022.json",
        "description": "First trade on or before 31 Dec 2021",
    },
    "Uncle (≤2022)": {
        "slug": "unc",
        "path": DATA_DIR / "opensea_og_percentile_distribution_pre2023.json",
        "description": "First trade on or before 31 Dec 2022",
    },
    "Cousin (≤2023)": {
        "slug": "cuz",
        "path": DATA_DIR / "opensea_og_percentile_distribution_pre2024.json",
        "description": "First trade on or before 31 Dec 2023",
    },
}

DUNE_API_KEY = os.getenv("DUNE_API_KEY")
DEMO_WALLET = os.getenv("DEMO_WALLET", "")


if "tier_pct" not in st.session_state:
    st.session_state["tier_pct"] = 10.0
if "cohort_size" not in st.session_state:
    st.session_state["cohort_size"] = 100_000
if "og_pool_pct" not in st.session_state:
    st.session_state["og_pool_pct"] = 15
if "fdv_billion" not in st.session_state:
    st.session_state["fdv_billion"] = 4


@st.cache_data(show_spinner=False)
def load_distribution(path_str: str) -> List[Dict[str, Any]]:
    path = Path(path_str)
    if not path.exists():
        return []
    with path.open() as f:
        payload = json.load(f)
    if isinstance(payload, dict) and "result" in payload:
        rows = payload.get("result", {}).get("rows", [])
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    return sorted(rows, key=lambda row: row.get("usd_percentile_rank", 0))


def estimate_og_cohort_size(distribution: List[Dict[str, Any]]) -> int:
    if not distribution:
        return 0
    return sum(int(entry.get("wallet_count") or 0) for entry in distribution)


def determine_percentile_band(
    total_usd: float,
    distribution: List[Dict[str, Any]],
    cohort_size: int,
) -> Dict[str, Any] | None:
    if not distribution or cohort_size <= 0:
        return None

    remaining = cohort_size
    cumulative_before = 0

    for idx, entry in enumerate(distribution):
        bucket_count = int(entry.get("wallet_count") or 0)
        if bucket_count <= 0:
            continue

        take = min(bucket_count, remaining)
        if take <= 0:
            break

        band_start_rank = cumulative_before
        band_end_rank = cumulative_before + take

        min_usd = float(entry.get("min_total_usd") or 0.0)
        max_usd = float(entry.get("max_total_usd") or min_usd)

        in_bucket = min_usd <= total_usd <= max_usd
        is_last_bucket = remaining <= take

        if in_bucket or (is_last_bucket and total_usd < min_usd):
            start_percentile = band_start_rank / cohort_size * 100
            end_percentile = band_end_rank / cohort_size * 100
            return {
                "start_percentile": start_percentile,
                "end_percentile": min(100.0, end_percentile),
                "band_wallets": take,
                "band_wallets_full": bucket_count,
                "wallets_before": band_start_rank,
                "bucket_index": idx,
                "bucket_data": entry,
            }

        cumulative_before = band_end_rank
        remaining -= take

        if remaining <= 0:
            break

    return None


@st.cache_data(show_spinner=False, ttl=300)
def fetch_wallet_report(address: str) -> Dict[str, Any]:
    if not DUNE_API_KEY:
        raise RuntimeError("DUNE_API_KEY not configured")
    params = {"wallet": address, "limit": 1000}
    url = f"https://api.dune.com/api/v1/query/{DUNE_QUERY_WALLET_STATS_ID}/results"
    response = requests.get(url, headers={"X-Dune-API-Key": DUNE_API_KEY}, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    rows = data.get("result", {}).get("rows", [])
    if not rows:
        return {}
    summary = next((row for row in rows if row.get("section") == "summary"), None)
    buyer_seller = [row for row in rows if row.get("section") == "buyer_seller"]
    collections = [row for row in rows if row.get("section") == "collection"]
    return {
        "summary": summary,
        "buyer_seller": buyer_seller,
        "collections": collections,
    }
TOTAL_SUPPLY = 1_000_000_000
DEFAULT_REVEAL_DURATION = 6


@dataclass
class ScenarioResult:
    share_pct: float
    fdv_billion: float
    tokens_per_wallet: float
    usd_value: float


def compute_scenario(
    *,
    total_supply: int,
    og_pool_pct: float,
    fdv_billion: float,
    cohort_size: int,
    tier_pct: float,
    share_pct: float,
) -> ScenarioResult:
    og_pool_tokens = total_supply * (og_pool_pct / 100)
    wallets_in_tier = max(1, cohort_size * (tier_pct / 100))
    tier_share_fraction = share_pct / 100
    tokens_per_wallet = og_pool_tokens * tier_share_fraction / wallets_in_tier

    token_price = (fdv_billion * 1_000_000_000) / total_supply
    usd_value = tokens_per_wallet * token_price

    return ScenarioResult(
        share_pct=share_pct,
        fdv_billion=fdv_billion,
        tokens_per_wallet=tokens_per_wallet,
        usd_value=usd_value,
    )


def build_share_table(
    share_pcts: Iterable[float],
    fdv_billion: float,
    *,
    total_supply: int,
    og_pool_pct: float,
    cohort_size: int,
    tier_pct: float,
) -> pd.DataFrame:
    rows: List[ScenarioResult] = []
    for share in share_pcts:
        rows.append(
            compute_scenario(
                total_supply=total_supply,
                og_pool_pct=og_pool_pct,
                fdv_billion=fdv_billion,
                cohort_size=cohort_size,
                tier_pct=tier_pct,
                share_pct=share,
            )
        )
    df = pd.DataFrame(
        {
            "Tier Share %": [r.share_pct for r in rows],
            "Tokens / Wallet": [round(r.tokens_per_wallet, 2) for r in rows],
            "USD": [round(r.usd_value, 2) for r in rows],
        }
    )
    return df


def build_heatmap_data(
    share_options: Iterable[float],
    fdv_options: Iterable[float],
    *,
    total_supply: int,
    og_pool_pct: float,
    cohort_size: int,
    tier_pct: float,
) -> pd.DataFrame:
    results: List[ScenarioResult] = []
    for share in share_options:
        for fdv in fdv_options:
            results.append(
                compute_scenario(
                    total_supply=total_supply,
                    og_pool_pct=og_pool_pct,
                    fdv_billion=fdv,
                    cohort_size=cohort_size,
                    tier_pct=tier_pct,
                    share_pct=share,
                )
            )
    df = pd.DataFrame(
        {
            "Tier Share %": [r.share_pct for r in results],
            "FDV ($B)": [r.fdv_billion for r in results],
            "Tokens / Wallet": [r.tokens_per_wallet for r in results],
            "USD": [r.usd_value for r in results],
        }
    )
    return df


def generate_cohort_slider_options(
    *,
    min_val: int = 50_000,
    mid_val: int = 100_000,
    max_val: int = 500_000,
    below_steps: int = 31,
    above_steps: int = 30,
) -> List[int]:
    """Return a non-linear set of cohort sizes with the midpoint anchored at ``mid_val``.

    Values are spaced geometrically below and above the midpoint so that mid_val sits near
    the centre of the slider while still giving reach to min and max bounds.
    """

    def _geomspace(start: float, stop: float, steps: int) -> List[float]:
        if steps <= 1:
            return [float(start)]
        ratio = (stop / start) ** (1 / (steps - 1))
        return [start * (ratio ** i) for i in range(steps)]

    below = _geomspace(min_val, mid_val, below_steps)
    above = _geomspace(mid_val, max_val, above_steps + 1)[1:]
    combined = list(below) + list(above)

    rounded = [int(round(value / 5_000) * 5_000) for value in combined]
    seen: set[int] = set()
    ordered_unique: List[int] = []
    for item in rounded:
        if item not in seen:
            seen.add(item)
            ordered_unique.append(item)
    return ordered_unique


def generate_percentile_options() -> List[float]:
    """Return tier percentile choices with higher resolution near the top cohorts."""

    fine_grain = [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 7.5, 10.0]
    broader = [12.5, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    return fine_grain + broader


def format_percentile_option(value: float) -> str:
    formatted = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"Top {formatted}%"


def run_reveal_presentation(steps: List[tuple[str, str]], duration_seconds: int) -> None:
    """Animate the reveal timeline with a progress bar and step narration."""

    timeline = st.container()
    progress = timeline.progress(0, text="Preparing SEA airdrop projection…")
    narration = timeline.empty()

    total_steps = max(len(steps), 1)
    # Avoid zero division and guarantee a minimum dwell per step.
    step_duration = max(duration_seconds / total_steps, 0.35)

    for idx, (title, detail) in enumerate(steps, start=1):
        progress.progress(
            int(idx / total_steps * 100),
            text=title,
        )
        narration.markdown(f"**{title}**\n\n{detail}")
        time.sleep(step_duration)

    progress.empty()
    narration.empty()
    st.success("Projection ready — scroll to view your estimated allocation.")


st.markdown(
    """
    <div style="text-align: center;">
        <h1 style="margin-bottom: 0.3rem;">OpenSea SEA Airdrop Estimator</h1>
        <p style="font-size: 1.05rem; color: #475569; margin-top: 0;">
            Model your allocation by dialling in launch dynamics, OG cohort positioning, and tier assumptions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #1d4ed8, #3b82f6);
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 600;
        padding: 0.95rem 3rem;
        border-radius: 18px;
        border: none;
        box-shadow: 0 15px 32px rgba(59, 130, 246, 0.32);
    }
    div[data-testid="stButton"] button[kind="primary"]:hover:not(:disabled) {
        box-shadow: 0 20px 36px rgba(59, 130, 246, 0.38);
        transform: translateY(-1px);
    }
    div[data-testid="stButton"] button[kind="primary"]:disabled {
        background: #94a3b8;
        box-shadow: none;
        cursor: not-allowed;
    }
    .insight-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: center;
        margin-top: 1.75rem;
    }
    .insight-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px;
        padding: 1rem 1.35rem;
        min-width: 180px;
        max-width: 240px;
        color: #e2e8f0;
    }
    .insight-card h4 {
        margin: 0 0 0.35rem 0;
        font-size: 0.85rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .insight-card .value {
        font-size: 1.55rem;
        font-weight: 600;
        margin: 0;
    }
    .insight-card .hint {
        margin-top: 0.2rem;
        font-size: 0.85rem;
        color: #cbd5f5;
        opacity: 0.85;
    }
    .stepper {
        margin-top: 2rem;
        background: rgba(15, 23, 42, 0.82);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 1.6rem 1.8rem;
        color: #e2e8f0;
    }
    .stepper h4 {
        margin: 0 0 1rem 0;
        text-align: center;
        font-size: 0.95rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .stepper-list {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin: 0;
        padding: 0;
        list-style: none;
    }
    .stepper-item {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
    }
    .stepper-index {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: #e2e8f0;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .stepper-content {
        flex: 1;
    }
    .stepper-content .title {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.15rem;
    }
    .stepper-content .detail {
        font-size: 0.95rem;
        color: #cbd5f5;
    }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stSlider"] label {
        color: #1d4ed8 !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

cohort_names = list(COHORT_CONFIG.keys())
available_cohorts = [name for name in cohort_names if COHORT_CONFIG[name]["path"].exists()]
default_cohort = (
    st.session_state.get("cohort_selection")
    or (available_cohorts[0] if available_cohorts else cohort_names[0])
)
if default_cohort not in cohort_names:
    default_cohort = cohort_names[0]

cohort_selection = st.radio(
    "Choose OG cohort definition",
    cohort_names,
    index=cohort_names.index(default_cohort),
)
st.session_state["cohort_selection"] = cohort_selection
selected_cohort_conf = COHORT_CONFIG[cohort_selection]
distribution_rows = load_distribution(str(selected_cohort_conf["path"]))

if description := selected_cohort_conf.get("description"):
    st.caption(description)

if not distribution_rows:
    st.warning(
        f"Percentile distribution file missing for {cohort_selection}. "
        f"Expected at {selected_cohort_conf['path']}"
    )

cohort_slider_options = generate_cohort_slider_options()

previous_selection = st.session_state.get("cohort_selection_prev")
st.session_state["cohort_selection_prev"] = cohort_selection

if distribution_rows:
    st.session_state["cohort_size_estimate"] = estimate_og_cohort_size(distribution_rows)

if (
    previous_selection is not None
    and previous_selection != cohort_selection
    and st.session_state.get("wallet_report")
    and distribution_rows
):
    summary = st.session_state["wallet_report"].get("summary", {})
    total_usd = float(summary.get("total_usd") or 0.0)
    band_info = determine_percentile_band(
        total_usd,
        distribution_rows,
        st.session_state.get("cohort_size", 100_000),
    )
    st.session_state["wallet_band"] = band_info
    if band_info:
        mid_percentile = (
            band_info.get("start_percentile", 0.0) + band_info.get("end_percentile", 0.0)
        ) / 2
        st.session_state["tier_pct"] = float(max(0.1, min(100.0, mid_percentile)))

wallet_holder = st.container()

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

    if fetch_clicked:
        if not wallet_address:
            st.warning("Enter a wallet address to fetch OpenSea activity.")
        else:
            try:
                with st.spinner("Contacting Dune …"):
                    report = fetch_wallet_report(wallet_address)
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
                    cohort_estimate = estimate_og_cohort_size(distribution_rows)
                    if cohort_estimate:
                        st.session_state["cohort_size_estimate"] = cohort_estimate
                    st.session_state["wallet_address"] = wallet_address
                    st.success("Wallet snapshot updated. Scroll down to view personalised metrics.")
            except RuntimeError as err:
                st.error(str(err))
            except requests.exceptions.RequestException as err:
                st.error(f"Failed to fetch wallet data: {err}")

wallet_report = st.session_state.get("wallet_report")
wallet_band = st.session_state.get("wallet_band")

if wallet_report and distribution_rows:
    summary_snapshot = wallet_report.get("summary", {})
    total_usd_snapshot = float(summary_snapshot.get("total_usd") or 0.0)
    recomputed_band = determine_percentile_band(
        total_usd_snapshot,
        distribution_rows,
        cohort_size,
    )
    st.session_state["wallet_band"] = recomputed_band
    wallet_band = recomputed_band

if wallet_report and wallet_report.get("summary"):
    summary = wallet_report["summary"]
    first_trade = pd.to_datetime(summary.get("first_trade")) if summary.get("first_trade") else None
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

    cohort_estimate = st.session_state.get("cohort_size_estimate")
    if cohort_estimate:
        st.caption(
            f"{cohort_selection}: approximately {cohort_estimate:,} wallets qualify under this definition. "
            "Use the cohort size slider below to focus on your own OG definition."
        )

cta_col = st.container()

total_supply = TOTAL_SUPPLY

with st.container():
    top_row = st.columns(4)

    with top_row[0]:
        st.markdown("**OG/community allocation (%)**")
        st.caption("Portion of supply earmarked for historical users.")
        og_pool_pct = st.slider(
            "OG/community allocation (%)",
            min_value=10,
            max_value=25,
            step=1,
            label_visibility="collapsed",
            key="og_pool_pct",
        )

    with top_row[1]:
        st.markdown("**Launch FDV ($B)**")
        st.caption("Fully diluted valuation at token generation event.")
        fdv_billion = float(
            st.select_slider(
                "Launch FDV ($B)",
                options=[2, 3, 4, 5, 6, 7],
                format_func=lambda val: f"${val}B",
                label_visibility="collapsed",
                key="fdv_billion",
            )
        )

    with top_row[2]:
        st.markdown("**OG cohort size (wallets)**")
        st.caption("Estimated wallets eligible for OG rewards.")
        current_cohort_value = st.session_state.get("cohort_size", 100_000)
        if current_cohort_value not in cohort_slider_options:
            nearest = min(cohort_slider_options, key=lambda opt: abs(opt - current_cohort_value))
            st.session_state["cohort_size"] = nearest
            current_cohort_value = nearest
        cohort_size = st.select_slider(
            "OG cohort size (wallets)",
            options=cohort_slider_options,
            format_func=lambda val: f"{val:,}",
            label_visibility="collapsed",
            key="cohort_size",
        )

    with top_row[3]:
        st.markdown("**Your percentile band (%)**")
        st.caption("Where you believe you sit within OGs.")
        percentile_options = generate_percentile_options()
        tier_pct = st.select_slider(
            "Your percentile band (%)",
            options=percentile_options,
            format_func=format_percentile_option,
            label_visibility="collapsed",
            key="tier_pct",
        )

    st.markdown("---")

    scenario_cols = st.columns(2)
    with scenario_cols[0]:
        st.markdown("**Tier share comparisons**")
        default_share_options = [20, 30, 40]
        share_options = st.multiselect(
            "Tier share percentages to compare",
            options=[10, 15, 20, 25, 30, 35, 40, 45, 50],
            default=default_share_options,
        )
        if not share_options:
            share_options = default_share_options
        st.caption("The first selection powers the featured scenario.")

    with scenario_cols[1]:
        st.markdown("**FDV sensitivities**")
        fdv_sensitivity = st.multiselect(
            "FDV points ($B)",
            options=[3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
            default=[3.0, 4.0, 5.0],
        )
        if fdv_billion not in fdv_sensitivity:
            fdv_sensitivity.append(fdv_billion)
            fdv_sensitivity = sorted(set(fdv_sensitivity))
        st.caption("Optional extra FDV points you might want to analyze later.")


reveal_duration = DEFAULT_REVEAL_DURATION


token_price = (fdv_billion * 1_000_000_000) / total_supply
wallets_in_tier = max(1, math.floor(cohort_size * (tier_pct / 100)))
og_pool_tokens = total_supply * (og_pool_pct / 100)
featured_share = share_options[0]

selected_scenario = compute_scenario(
    total_supply=total_supply,
    og_pool_pct=og_pool_pct,
    fdv_billion=fdv_billion,
    cohort_size=cohort_size,
    tier_pct=tier_pct,
    share_pct=featured_share,
)

steps_for_reveal = [
    (
        "Token price",
        f"FDV ${fdv_billion:,.0f}B / {total_supply:,} SEA = ${token_price:,.2f} per token",
    ),
    (
        "OG pool allocation",
        f"{og_pool_pct}% of supply reserved for OGs → {og_pool_tokens:,.0f} SEA available to distribute",
    ),
    (
        "Tier sizing",
        f"{format_percentile_option(tier_pct)} equates to roughly {wallets_in_tier:,} wallets competing",
    ),
    (
        "Tier share assumption",
        f"Using a {featured_share}% slice of the OG pool for your tier gives {selected_scenario.tokens_per_wallet:,.0f} SEA each",
    ),
    (
        "Estimated payout",
        f"At ${token_price:,.2f}/SEA that works out to ≈ ${selected_scenario.usd_value:,.0f}",
    ),
]

current_signature = (
    og_pool_pct,
    fdv_billion,
    cohort_size,
    tier_pct,
    tuple(share_options),
    tuple(fdv_sensitivity),
)

if "has_revealed_once" not in st.session_state:
    st.session_state.has_revealed_once = False
if "last_reveal_signature" not in st.session_state:
    st.session_state.last_reveal_signature = None

hero_container = st.container()

def _format_step_detail(text: str) -> str:
    return html.escape(text)


def render_hero() -> None:
    usd_value = selected_scenario.usd_value
    sea_amount = selected_scenario.tokens_per_wallet

    with hero_container:
        st.markdown(
            f"""
            <div style="background: radial-gradient(circle at top left, #0f172a, #1f2937); color: #ffffff; padding: 2.5rem; border-radius: 18px; text-align: center; margin-top: 1.5rem;">
                <div style="font-size:0.85rem; letter-spacing:0.18em; text-transform:uppercase; opacity:0.75;">Estimated payout</div>
                <div style="font-size:3.1rem; font-weight:700; margin:0.65rem 0;">${usd_value:,.0f}</div>
                <div style="font-size:1.15rem; opacity:0.9;">≈ {sea_amount:,.0f} SEA at ${token_price:,.2f} per token</div>
                <div style="margin-top:1.1rem; font-size:0.95rem; opacity:0.85;">Featured tier captures {featured_share}% of the OG pool.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        insight_cards_html = "".join(
            f"""
            <div class='insight-card'>
                <h4>{html.escape(label)}</h4>
                <div class='value'>{html.escape(value)}</div>
                <div class='hint'>{html.escape(hint)}</div>
            </div>
            """
            for label, value, hint in insights
        )
        st.markdown(
            f"<div class='insight-grid'>{insight_cards_html}</div>",
            unsafe_allow_html=True,
        )

        steps_html = "".join(
            f"""
            <li class='stepper-item'>
                <div class='stepper-index'>{idx}</div>
                <div class='stepper-content'>
                    <div class='title'>{html.escape(title)}</div>
                    <div class='detail'>{_format_step_detail(detail)}</div>
                </div>
            </li>
            """
            for idx, (title, detail) in enumerate(steps_for_reveal, start=1)
        )
        st.markdown(
            f"""
            <div class='stepper'>
                <h4>How we got here</h4>
                <ul class='stepper-list'>
                    {steps_html}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


with cta_col:
    left_spacer, button_area, right_spacer = st.columns([3, 2, 3])
    with button_area:
        clicked = st.button(
            "Estimate my airdrop",
            key="estimate_cta",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.has_revealed_once,
        )
    if clicked:
        run_reveal_presentation(steps_for_reveal, reveal_duration)
        st.session_state.has_revealed_once = True
        st.session_state.last_reveal_signature = current_signature
        st.rerun()

if st.session_state.has_revealed_once:
    inputs_changed = False
    if (
        st.session_state.last_reveal_signature is not None
        and st.session_state.last_reveal_signature != current_signature
    ):
        inputs_changed = True
        st.session_state.last_reveal_signature = current_signature

    if inputs_changed:
        st.info("Inputs updated — the estimate refreshes instantly.")

    render_hero()
