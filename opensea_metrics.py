#!/usr/bin/env python3
"""Utility helpers for OpenSea wallet analytics.

Features
--------
- Summarise existing CSV exports (e.g., from Dune) stored inside a zip file.
- Optionally refresh raw trade/sales data from Dune API, given query IDs and API key.

Example usage
-------------
Summarise the shipped reports:
    python opensea_metrics.py summarize --zip opensea_reports.zip

Fetch fresh data from Dune (requires API key):
    DUNE_API_KEY=... python opensea_metrics.py fetch \
        --wallet 0xd86Be55512f44e643f410b743872879B174812Fd \
        --trades-query 3055142 --sales-query 3055143 \
        --out opensea_reports_new.zip

"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from io import TextIOWrapper
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import requests
except ImportError:  # pragma: no cover - provide a nicer message when requests is missing
    requests = None

# --------- Data containers ---------

@dataclass
class Trade:
    timestamp: datetime
    direction: str
    collection: str
    contract: str
    token_id: str
    price_eth: Decimal
    protocol: Optional[str] = None
    tx_hash: Optional[str] = None
    marketplace_fee_eth: Decimal = Decimal("0")
    royalty_fee_eth: Decimal = Decimal("0")


@dataclass
class Sale:
    timestamp: datetime
    collection: str
    contract: str
    token_id: str
    proceeds_eth: Decimal
    payment_assets: Optional[str] = None
    tx_hash: Optional[str] = None
    marketplace_fee_eth: Decimal = Decimal("0")
    royalty_fee_eth: Decimal = Decimal("0")


# --------- Parsing helpers ---------

ISO8601_FORMATS: Sequence[str] = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
)


def parse_timestamp(value: str) -> datetime:
    for fmt in ISO8601_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value}")


def parse_decimal(value: str) -> Decimal:
    value = value.strip()
    if not value:
        return Decimal("0")
    return Decimal(value)


def parse_optional_decimal(row: Dict[str, str], *names: str) -> Decimal:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return parse_decimal(str(row[name]))
    return Decimal("0")


def _normalise_direction(direction: Optional[str]) -> str:
    if not direction:
        return "unknown"
    return direction.strip().lower()


def load_trades(rows: Iterable[Dict[str, str]]) -> List[Trade]:
    trades: List[Trade] = []
    for row in rows:
        try:
            ts = parse_timestamp(row["timestamp"])
        except KeyError:
            raise KeyError("Trade row is missing required 'timestamp' column")
        direction = _normalise_direction(row.get("direction"))

        marketplace_fee = parse_optional_decimal(row, "marketplace_fee_eth", "platform_fee_eth", "opensea_fee_eth", "fee_eth")
        royalty_fee = parse_optional_decimal(row, "royalty_fee_eth", "creator_fee_eth", "royalty_eth")

        trade = Trade(
            timestamp=ts,
            direction=direction,
            collection=row.get("collection", ""),
            contract=row.get("contract", ""),
            token_id=row.get("token_id", ""),
            price_eth=parse_decimal(row.get("price_eth", "0")),
            protocol=row.get("protocol"),
            tx_hash=row.get("tx_hash"),
            marketplace_fee_eth=marketplace_fee,
            royalty_fee_eth=royalty_fee,
        )
        trades.append(trade)
    return trades


def load_sales(rows: Iterable[Dict[str, str]]) -> List[Sale]:
    sales: List[Sale] = []
    for row in rows:
        try:
            ts = parse_timestamp(row["timestamp"])
        except KeyError:
            raise KeyError("Sale row is missing required 'timestamp' column")
        marketplace_fee = parse_optional_decimal(row, "marketplace_fee_eth", "platform_fee_eth", "opensea_fee_eth", "fee_eth")
        royalty_fee = parse_optional_decimal(row, "royalty_fee_eth", "creator_fee_eth", "royalty_eth")
        sale = Sale(
            timestamp=ts,
            collection=row.get("collection", ""),
            contract=row.get("contract", ""),
            token_id=row.get("token_id", ""),
            proceeds_eth=parse_decimal(row.get("proceeds_eth", "0")),
            payment_assets=row.get("payment_assets"),
            tx_hash=row.get("tx_hash"),
            marketplace_fee_eth=marketplace_fee,
            royalty_fee_eth=royalty_fee,
        )
        sales.append(sale)
    return sales


# --------- Zip helpers ---------

DEFAULT_TRADES_FILE = "d86_opensea_trades.csv"
DEFAULT_SALES_FILE = "d86_opensea_sales.csv"


def read_csv_from_zip(zip_path: Path, filename: str) -> List[Dict[str, str]]:
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        try:
            with archive.open(filename) as handle:
                text_handle = TextIOWrapper(handle, encoding="utf-8")
                reader = csv.DictReader(text_handle)
                return list(reader)
        except KeyError:
            raise FileNotFoundError(f"Zip archive {zip_path} does not contain {filename}")


def write_csvs_to_zip(zip_path: Path, trades: Sequence[Dict[str, str]], sales: Sequence[Dict[str, str]], *,
                      trades_filename: str = DEFAULT_TRADES_FILE,
                      sales_filename: str = DEFAULT_SALES_FILE) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, mode="w") as archive:
        def _write(filename: str, rows: Sequence[Dict[str, str]]):
            if not rows:
                return
            fieldnames = list(rows[0].keys())
            with archive.open(filename, mode="w") as handle:
                text_handle = TextIOWrapper(handle, encoding="utf-8", newline="")
                writer = csv.DictWriter(text_handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
                text_handle.flush()

        _write(trades_filename, trades)
        _write(sales_filename, sales)


# --------- Metrics ---------

@dataclass
class WalletSummary:
    wallet: Optional[str]
    first_activity: datetime
    last_activity: datetime
    buys: int
    buys_volume_eth: Decimal
    sells: int
    sells_volume_eth: Decimal
    net_realised_eth: Decimal
    marketplace_fees_eth: Decimal
    royalty_fees_eth: Decimal
    unique_collections: int
    unique_tokens: int
    trade_count: int
    fills_count: int
    active_days: int
    active_weeks: int
    active_months: int
    days_since_first_trade: int


def summarise_wallet(trades: Sequence[Trade], sales: Sequence[Sale], wallet: Optional[str] = None) -> WalletSummary:
    if not trades and not sales:
        raise ValueError("No trade or sale records to summarise")

    timestamps = [entry.timestamp for entry in trades] + [entry.timestamp for entry in sales]
    first_activity = min(timestamps)
    last_activity = max(timestamps)

    buy_trades = [t for t in trades if t.direction == "buy"]
    sell_trades = [t for t in trades if t.direction == "sell"]

    buys_volume = sum((t.price_eth for t in buy_trades), Decimal("0"))
    # Some data exports include outgoing sales as trades with direction "sell".
    sells_volume_from_trades = sum((t.price_eth for t in sell_trades), Decimal("0"))

    sells_volume = sum((s.proceeds_eth for s in sales), sells_volume_from_trades)
    sells_count = len(sales) if sales else len(sell_trades)

    unique_tokens = {(t.contract, t.token_id) for t in trades}
    unique_tokens.update((s.contract, s.token_id) for s in sales)
    unique_collections = {t.collection for t in trades if t.collection}
    unique_collections.update(s.collection for s in sales if s.collection)

    fills_count = len(trades) + len(sales)
    active_days = {ts.date() for ts in timestamps}
    active_weeks = {(ts.isocalendar().year, ts.isocalendar().week) for ts in timestamps}
    active_months = {(ts.year, ts.month) for ts in timestamps}

    net_realised = sells_volume - buys_volume

    marketplace_fees = sum((t.marketplace_fee_eth for t in trades), Decimal("0"))
    marketplace_fees += sum((s.marketplace_fee_eth for s in sales), Decimal("0"))
    royalty_fees = sum((t.royalty_fee_eth for t in trades), Decimal("0"))
    royalty_fees += sum((s.royalty_fee_eth for s in sales), Decimal("0"))

    days_since_first = (datetime.now(timezone.utc) - first_activity).days

    return WalletSummary(
        wallet=wallet,
        first_activity=first_activity,
        last_activity=last_activity,
        buys=len(buy_trades),
        buys_volume_eth=buys_volume,
        sells=sells_count,
        sells_volume_eth=sells_volume,
        net_realised_eth=net_realised,
        marketplace_fees_eth=marketplace_fees,
        royalty_fees_eth=royalty_fees,
        unique_collections=len(unique_collections),
        unique_tokens=len(unique_tokens),
        trade_count=len(trades),
        fills_count=fills_count,
        active_days=len(active_days),
        active_weeks=len(active_weeks),
        active_months=len(active_months),
        days_since_first_trade=days_since_first,
    )


def print_summary(summary: WalletSummary) -> None:
    wallet_label = summary.wallet or "(unknown wallet)"
    print(f"Wallet: {wallet_label}")
    print(f"First activity: {summary.first_activity.isoformat()}")
    print(f"Last activity: {summary.last_activity.isoformat()}")
    print("---")
    print(f"Buys: {summary.buys} | Volume: {summary.buys_volume_eth} ETH")
    print(f"Sales: {summary.sells} | Volume: {summary.sells_volume_eth} ETH")
    print(f"Net realised P&L: {summary.net_realised_eth} ETH")
    print("---")
    if summary.marketplace_fees_eth:
        print(f"Marketplace fees paid: {summary.marketplace_fees_eth} ETH")
    else:
        print("Marketplace fees paid: (not present in dataset)")
    if summary.royalty_fees_eth:
        print(f"Royalties paid: {summary.royalty_fees_eth} ETH")
    else:
        print("Royalties paid: (not present in dataset)")
    print("---")
    print(f"Unique collections: {summary.unique_collections}")
    print(f"Unique tokens traded: {summary.unique_tokens}")
    print(f"Trade rows: {summary.trade_count} | Total fills (trade+sales rows): {summary.fills_count}")
    print(f"Active periods: {summary.active_days} days | {summary.active_weeks} weeks | {summary.active_months} months")
    print(f"Days since first trade: {summary.days_since_first_trade}")


# --------- Dune integration ---------

DUNE_BASE = "https://api.dune.com/api/v1"
DEFAULT_PARAMETER_KEY = "address"
DEFAULT_PARAM_FALLBACKS = (
    "address",
    "wallet_address",
    "address_t0145f",
    "wallet",
)


class DuneClient:
    def __init__(self, api_key: str, *, timeout: int = 30):
        if requests is None:
            raise RuntimeError("The 'requests' package is required for Dune API calls. Install it via pip first.")
        self.session = requests.Session()
        self.session.headers.update({"X-DUNE-API-KEY": api_key})
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs):
        url = f"{DUNE_BASE}{path}"
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        if response.status_code == 404:
            return None
        if not response.ok:
            raise RuntimeError(f"Dune API error {response.status_code}: {response.text}")
        return response.json()

    def get_results(self, query_id: int, params: Dict[str, str]) -> Optional[Dict]:
        payload = {"parameters": params} if params else None
        return self._request("GET", f"/query/{query_id}/results", params=payload)

    def execute_query(self, query_id: int, params: Dict[str, str]) -> str:
        body = {"query_parameters": params}
        data = self._request("POST", f"/query/{query_id}/execute", json=body)
        if not data or "execution_id" not in data:
            raise RuntimeError(f"Unexpected response while executing Dune query {query_id}: {data}")
        return data["execution_id"]

    def wait_for_execution(self, execution_id: str, *, poll_seconds: int = 5, timeout_seconds: int = 120) -> Dict:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            data = self._request("GET", f"/execution/{execution_id}/status")
            if data and data.get("state") in {"QUERY_STATE_COMPLETED"}:
                return data
            if data and data.get("state") in {"QUERY_STATE_FAILED", "QUERY_STATE_TIMEOUT"}:
                raise RuntimeError(f"Dune execution failed: {json.dumps(data)}")
            time.sleep(poll_seconds)
        raise TimeoutError(f"Timed out waiting for Dune execution {execution_id}")

    def get_execution_results(self, execution_id: str) -> Dict:
        data = self._request("GET", f"/execution/{execution_id}/results")
        if not data:
            raise RuntimeError(f"No results found for execution {execution_id}")
        return data


def determine_parameter_payload(wallet: str, explicit_key: Optional[str] = None) -> Dict[str, str]:
    if explicit_key:
        return {explicit_key: wallet}
    return {key: wallet for key in DEFAULT_PARAM_FALLBACKS}


def fetch_dune_rows(client: DuneClient, query_id: int, wallet: str, parameter_key: Optional[str] = None) -> List[Dict[str, str]]:
    if query_id <= 0:
        raise ValueError("Dune query id must be positive")
    parameter_attempts = [parameter_key] if parameter_key else list(DEFAULT_PARAM_FALLBACKS)

    for key in filter(None, parameter_attempts):
        params = {key: wallet}
        data = client.get_results(query_id, params)
        if data and data.get("result") and data["result"].get("rows"):
            return data["result"]["rows"]
        execution_id = client.execute_query(query_id, params)
        client.wait_for_execution(execution_id)
        result = client.get_execution_results(execution_id)
        if result and result.get("result") and result["result"].get("rows"):
            return result["result"]["rows"]
    raise RuntimeError(f"Unable to fetch results for query {query_id} with provided wallet parameter")


# --------- CLI ---------


def cmd_summarize(args: argparse.Namespace) -> None:
    zip_path = Path(args.zip)
    trades_filename = args.trades or DEFAULT_TRADES_FILE
    sales_filename = args.sales or DEFAULT_SALES_FILE

    trade_rows = read_csv_from_zip(zip_path, trades_filename)
    sales_rows = read_csv_from_zip(zip_path, sales_filename)

    trades = load_trades(trade_rows)
    sales = load_sales(sales_rows)
    summary = summarise_wallet(trades, sales, wallet=args.wallet)
    print_summary(summary)


def cmd_fetch(args: argparse.Namespace) -> None:
    api_key = args.api_key or Path(args.api_key_file).read_text().strip() if args.api_key_file else None
    if not api_key:
        api_key = os.environ.get("DUNE_API_KEY")
    if not api_key:
        raise SystemExit("Dune API key not provided. Use --api-key, --api-key-file, or set DUNE_API_KEY env variable.")

    client = DuneClient(api_key)
    wallet = args.wallet

    trades_rows = fetch_dune_rows(client, args.trades_query, wallet, args.parameter_key)
    sales_rows = fetch_dune_rows(client, args.sales_query, wallet, args.parameter_key)

    if args.out:
        out_path = Path(args.out)
        write_csvs_to_zip(out_path, trades_rows, sales_rows,
                          trades_filename=args.trades_filename or DEFAULT_TRADES_FILE,
                          sales_filename=args.sales_filename or DEFAULT_SALES_FILE)
        print(f"Saved updated dataset to {out_path}")

    trades = load_trades(trades_rows)
    sales = load_sales(sales_rows)
    summary = summarise_wallet(trades, sales, wallet=wallet)
    print_summary(summary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenSea wallet analytics helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize = subparsers.add_parser("summarize", help="Summarise local CSV exports inside a zip file")
    summarize.add_argument("--zip", default="opensea_reports.zip", help="Path to the zip archive containing exports")
    summarize.add_argument("--trades", dest="trades", help="CSV filename for trades inside the zip")
    summarize.add_argument("--sales", dest="sales", help="CSV filename for sales inside the zip")
    summarize.add_argument("--wallet", dest="wallet", help="Optional wallet address to display in the summary")
    summarize.set_defaults(func=cmd_summarize)

    fetch = subparsers.add_parser("fetch", help="Fetch fresh trade/sales data from Dune and summarise")
    fetch.add_argument("--wallet", required=True, help="Wallet address to analyse")
    fetch.add_argument("--trades-query", type=int, required=True, help="Dune query id returning trade rows")
    fetch.add_argument("--sales-query", type=int, required=True, help="Dune query id returning sale rows")
    fetch.add_argument("--parameter-key", help="Explicit query parameter key for the wallet address")
    fetch.add_argument("--api-key", help="Dune API key")
    fetch.add_argument("--api-key-file", help="Path to a file containing the Dune API key")
    fetch.add_argument("--out", help="Optional path to write the fetched CSVs as a zip archive")
    fetch.add_argument("--trades-filename", help="Filename to use inside the zip for trades")
    fetch.add_argument("--sales-filename", help="Filename to use inside the zip for sales")
    fetch.set_defaults(func=cmd_fetch)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
