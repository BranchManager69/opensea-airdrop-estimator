# OpenSea SEA Airdrop Estimator

Interactive Streamlit app for modelling OpenSea's SEA airdrop using real on-chain activity. Paste an Ethereum address, pull the wallet's OpenSea history from Dune, and see where it lands inside curated OG cohorts ("Super OG" ≤ 2021, "UNC" ≤ 2022, "Cousin" ≤ 2023). The tool automatically maps volume into percentile bands, projects payouts with adjustable levers, and highlights cohort stats to sanity‑check assumptions.

## Features

- **Wallet lookup** – fetches trade count, volume, platform/royalty fees via Dune query `5850749` using your `DUNE_API_KEY`.
- **Cohort selector** – toggle between pre‑2022, pre‑2023, and pre‑2024 OG definitions. Percentile math respects whichever cohort size you pick.
- **Slider levers** – adjust OG pool %, launch FDV, cohort size, and your percentile band. Defaults auto-tune based on fetched wallet stats.
- **Reveal flow** – animated breakdown of token price, pool allocation, tier sizing, and payout. Shows "historic vs now" insight placeholders for future extensions.
- **Cohort datasets** – curated percentile bands generated from Dune queries (`dune_queries/`) with filters to strip wash trades and insane outliers. Corresponding JSON files live under `data/`.

## Quick start

1. Install dependencies (Python 3.12+ recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # or pip install streamlit requests pandas altair python-dotenv
   ```

2. Create `.env` with your credentials:

   ```bash
   cat <<'ENV' > .env
   DUNE_API_KEY=your_dune_api_key
   DEMO_WALLET=0xd86Be55512f44e643f410b743872879B174812Fd
   ENV
   ```

3. Launch Streamlit:

   ```bash
   streamlit run sea_airdrop_dashboard.py
   ```

4. Open the local URL, choose an OG cohort, paste a wallet (or use the demo), and hit **Fetch history**. The estimator will auto-fill sliders based on the wallet's percentile.

## Repo layout

```
sea_airdrop_dashboard.py        # Streamlit app
requirements.txt                # minimal Python deps (generate with pip freeze if needed)
data/
  opensea_og_percentile_distribution_pre2022.json  # Super OG percentiles (≤ 2021)
  opensea_og_percentile_distribution_pre2023.json  # UNC cohort (≤ 2022)
  opensea_og_percentile_distribution_pre2024.json  # Cousin cohort (≤ 2023)
dune_queries/
  opensea_og_percentile_distribution_pre2022.sql   # Cohort generation queries
  opensea_og_percentile_distribution_pre2023.sql
  opensea_og_percentile_distribution_pre2024.sql
OpenSea_SEA_Airdrop_Outlook.md  # original analysis memo
opensea_metrics.py              # legacy CLI helper (summaries, CSV exports)
```

## Maintaining the cohort files

1. Run the SQL in `dune_queries/` inside Dune (each returns 100 rows).
2. Download the JSON results and overwrite the matching files in `data/`.
3. Restart the app; the cohort selector will automatically pick up the new thresholds.

If you want a different OG definition (e.g. first trade before mid‑2022 or minimum fee thresholds), tweak the SQL filters (`amount_usd`, `amount_original`, `platform_fee_amount`) and rerun. The app will adapt as long as the JSON schema remains the same (`usd_percentile_rank`, `wallet_count`, `min_total_usd`, `max_total_usd`, etc.).

## Developing further

- Add "historic vs today" USD comparison by multiplying wallet `total_eth` with a live ETH price feed and displaying delta.
- Overlay percentile charts (Altair) with markers so users can visually inspect where their wallet sits in the distribution.
- Materialize OG cohort snapshots in Dune or Supabase if the JSON files get unwieldy.

## License

MIT. Contributions welcome—open an issue or PR.
