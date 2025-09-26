"""Global configuration and constants for the Sea Mom app."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Resolve project paths -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOGOMARK_PATH = ASSETS_DIR / "opensea_logomark.png"

# Load environment variables _after_ paths are available so `.env` at root is found.
load_dotenv()

# External data configuration -----------------------------------------------
DUNE_QUERY_WALLET_STATS_ID = 5850749
DUNE_API_KEY = os.getenv("DUNE_API_KEY")
DEMO_WALLET = os.getenv("DEMO_WALLET", "")

SHARE_SERVICE_URL = os.getenv("SHARE_SERVICE_URL", "http://127.0.0.1:4076")
SHARE_PUBLIC_BASE = os.getenv("SHARE_PUBLIC_BASE") or os.getenv("BASE_URL", "")

# App-wide constants --------------------------------------------------------
TOTAL_SUPPLY = 1_000_000_000
DEFAULT_REVEAL_DURATION = 6

COHORT_CONFIG: Dict[str, Dict[str, Any]] = {
    "Super OG (≤2021)": {
        "slug": "super_og",
        "path": DATA_DIR / "opensea_og_percentile_distribution_pre2022.json",
        "description": "First trade on or before 31 Dec 2021",
        "timeline_label": "≤2021",
        "title": "Super OG",
        "tagline": "Pre-2022 traders",
    },
    "Uncle (≤2022)": {
        "slug": "unc",
        "path": DATA_DIR / "opensea_og_percentile_distribution_pre2023.json",
        "description": "First trade on or before 31 Dec 2022",
        "timeline_label": "≤2022",
        "title": "Uncle",
        "tagline": "First active in 2022",
    },
    "Cousin (≤2023)": {
        "slug": "cuz",
        "path": DATA_DIR / "opensea_og_percentile_distribution_pre2024.json",
        "description": "First trade on or before 31 Dec 2023",
        "timeline_label": "≤2023",
        "title": "Cousin",
        "tagline": "Joined by 2023",
    },
}


def resolve_page_icon() -> str:
    """Return a path or emoji suitable for `st.set_page_config` icon."""

    return str(LOGOMARK_PATH) if LOGOMARK_PATH.exists() else "🌊"
