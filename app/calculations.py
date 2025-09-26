"""Computation utilities for SEA airdrop projections."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd


@dataclass
class ScenarioResult:
    """Aggregated values for a single tier share / FDV combination."""

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
    *,
    total_supply: int,
    og_pool_pct: float,
    fdv_billion: float,
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
    """Return a non-linear set of cohort sizes with the midpoint anchored at ``mid_val``."""

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


def snap_value_to_options(value: float, options: Iterable[float]) -> float:
    """Return the entry in ``options`` closest to ``value``."""

    option_list = list(options)
    if not option_list:
        return value
    return min(option_list, key=lambda opt: abs(opt - value))


def round_to_step(value: float, step: int) -> int:
    return int(round(value / step) * step)


def round_up_to_step(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


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
