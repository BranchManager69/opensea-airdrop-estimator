"""Client for the share-card rendering service."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urljoin

import requests

from app.config import SHARE_PUBLIC_BASE, SHARE_SERVICE_URL


class ShareServiceError(RuntimeError):
    """Raised when the share-card service cannot fulfil a request."""


def _absolute_url(path: str, *, prefer_public: bool = False) -> str:
    if not path:
        return path
    if path.startswith("http://") or path.startswith("https://"):
        return path

    base = SHARE_PUBLIC_BASE if (prefer_public and SHARE_PUBLIC_BASE) else SHARE_SERVICE_URL
    if not base:
        return path
    base = base.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def create_share_card(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Request a new share card from the service and return normalised URLs."""

    if not SHARE_SERVICE_URL:
        raise ShareServiceError("Share service URL is not configured.")

    endpoint = SHARE_SERVICE_URL.rstrip("/") + "/cards"
    try:
        response = requests.post(endpoint, json=payload, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        raise ShareServiceError(f"Failed to create share card: {err}") from err

    try:
        data = response.json()
    except ValueError as err:
        raise ShareServiceError("Share service returned invalid JSON response.") from err

    card_id = data.get("id")
    if not card_id:
        raise ShareServiceError("Share service response missing card identifier.")

    image_url = _absolute_url(data.get("image_url", ""), prefer_public=True)
    share_url = _absolute_url(data.get("share_url", ""), prefer_public=True)
    meta_url = _absolute_url(data.get("meta_url", ""), prefer_public=True)

    return {
        "id": card_id,
        "image_url": image_url or "",
        "share_url": share_url or "",
        "meta_url": meta_url or "",
        "raw": data,
    }
