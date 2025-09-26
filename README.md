# OpenSea Wallet Utilities

- `OpenSea_SEA_Airdrop_Outlook.md` – analysis memo for wallet 0xd86Be55512f44e643f410b743872879B174812Fd.
- `opensea_reports.zip` – trade/sale CSV exports powering the memo.
- `opensea_metrics.py` – CLI helper to summarise existing exports (buys/sells, net P&L, marketplace + royalty fees when present) and optionally pull fresh rows from Dune when you supply a query id + API key.

## Quick Start

Summarise the bundled exports:

```bash
python3 opensea_metrics.py summarize --zip opensea_reports.zip \
  --wallet 0xd86Be55512f44e643f410b743872879B174812Fd
```

Fetch fresh data (needs the `requests` package and a Dune API key):

```bash
pip install requests  # first time only
export DUNE_API_KEY=your_key_here
python3 opensea_metrics.py fetch \
  --wallet 0xd86Be55512f44e643f410b743872879B174812Fd \
  --trades-query <query_id_for_trades> \
  --sales-query <query_id_for_sales> \
  --out opensea_reports_latest.zip
```

If your Dune query uses a non-standard wallet parameter name, pass it via `--parameter-key`.

The fetch command writes the raw CSVs back into a zip and prints the same summary stats, so you can drop the new zip into the memo workflow.

### Dune IDs referenced in the memo

- Trade-count percentile: query `2019952`
- Lifetime-volume percentile: query `1991670`
- First-trade cohort percentile: query `892164`
- Wallet economics snapshot (fees/royalties): dashboard `iceweasel/opensea-wallet-analyzer`

Open those inside Dune, duplicate them into your account, and reuse their IDs with the `fetch` subcommand. When your exported rows include `marketplace_fee_eth` or `royalty_fee_eth` columns, the summary automatically totals them.
