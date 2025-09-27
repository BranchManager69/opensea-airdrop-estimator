"""Data loading utilities for Sea Mom."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import time

import requests
import streamlit as st

from .config import DUNE_API_KEY, DUNE_QUERY_WALLET_STATS_ID


@st.cache_data(show_spinner=False)
def _load_distribution_cached(path_str: str, modified: float) -> List[Dict[str, Any]]:
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


def load_distribution(path: Path) -> List[Dict[str, Any]]:
    """Load percentile distribution rows from disk, with cache invalidation on mtime."""

    modified = path.stat().st_mtime if path.exists() else 0.0
    return _load_distribution_cached(str(path), modified)


def estimate_og_cohort_size(distribution: List[Dict[str, Any]]) -> int:
    """Return total wallet count represented in a percentile distribution payload."""

    if not distribution:
        return 0
    return sum(int(entry.get("wallet_count") or 0) for entry in distribution)


@st.cache_data(show_spinner=False, ttl=300)
def fetch_wallet_report(address: str) -> Dict[str, Any]:
    """Return summary + breakdown rows for the supplied wallet via Dune."""

    if not DUNE_API_KEY:
        raise RuntimeError("DUNE_API_KEY not configured")

    execution_url = f"https://api.dune.com/api/v1/query/{DUNE_QUERY_WALLET_STATS_ID}/execute"
    headers = {
        "X-Dune-API-Key": DUNE_API_KEY,
        "Content-Type": "application/json",
    }
    execute_response = requests.post(
        execution_url,
        headers=headers,
        json={"query_parameters": {"wallet": address}},
        timeout=30,
    )
    execute_response.raise_for_status()
    execution_id = execute_response.json().get("execution_id")
    if not execution_id:
        raise RuntimeError("Failed to start Dune execution")

    result_url = f"https://api.dune.com/api/v1/execution/{execution_id}/results"
    rows: List[Dict[str, Any]] = []
    for _ in range(15):
        result_response = requests.get(
            result_url,
            headers={"X-Dune-API-Key": DUNE_API_KEY},
            timeout=30,
        )
        result_response.raise_for_status()
        result_payload = result_response.json()
        state = result_payload.get("state")
        if state == "QUERY_STATE_COMPLETED":
            rows = result_payload.get("result", {}).get("rows", [])
            break
        if state in {"QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"}:
            message = result_payload.get("message") or "Execution failed"
            raise RuntimeError(message)
        time.sleep(1)
    else:
        raise RuntimeError("Timed out waiting for Dune execution")

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
