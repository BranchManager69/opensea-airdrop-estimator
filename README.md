<div align="center">

# Sea Mom

_OpenSea airdrop modelling with cinematic reveals, shareable flex cards, and Dune-powered wallet intelligence._

[![shell](https://img.shields.io/badge/shell-bash-4EAA25.svg)](#install--first-run)
[![python](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](#requirements)
[![streamlit](https://img.shields.io/badge/app-streamlit-FF4B4B.svg)](#install--first-run)
[![license](https://img.shields.io/github/license/BranchManager69/opensea.svg?color=blue)](#license)
[![live](https://img.shields.io/badge/live-sea.mom-0A66C2.svg)](https://sea.mom)

</div>

---

## Quick Navigation
- [Why Sea Mom](#why-sea-mom)
- [Requirements](#requirements)
- [Install & First Run](#install--first-run)
- [How It Works](#how-it-works)
- [Workflows](#workflows)
- [Configuration Cheat Sheet](#configuration-cheat-sheet)
- [Data & Security](#data--security)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Share Service](#share-service)
- [Roadmap](#roadmap)
- [Changelog](./OpenSea_SEA_Airdrop_Outlook.md)
- [License](#license)

## Why Sea Mom
Sea Mom turns OG OpenSea history into an airdrop projection that feels like an event, not a spreadsheet. It combines:
- **Wallet intelligence** – pull an address from Dune (query `5850749`), deduplicate trades, compute platform and royalty fees, and map USD volume into curated percentile bands.
- **Cinematic reveal** – a guided presentation walks through FDV, OG pool sizing, tier share, and final payout with narration, hero metrics, and inline validation charts.
- **Scenario storytelling** – three cohort cards stay in sync with a single slider, showing how assumptions shift across Super OG, Uncle, and Cousin definitions.
- **Instant share cards** – every reveal can mint a Sea Mom Flex PNG with your payout, tier, and cohort context, ready to copy or tweet.

## Requirements
- Python 3.12+
- Node.js 18+ (for the share-card microservice)
- `pip` and `npm`/`pnpm`
- `pm2` (optional, for process supervision)
- Valid [Dune API key](https://dune.com/docs/api/overview/)
- Optional: OpenSea domain (e.g., https://sea.mom) for production deployment

## Install & First Run
1. **Clone and install Python deps**
   ```bash
   git clone https://github.com/BranchManager69/opensea.git ~/tools/opensea
   cd ~/tools/opensea
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cat <<'ENV' > .env
   DUNE_API_KEY=your_dune_api_key
   DEMO_WALLET=0xd86Be55512f44e643f410b743872879B174812Fd
   BASE_URL=https://sea.mom
   APP_PUBLIC_BASE=https://sea.mom
   SHARE_SERVICE_URL=http://127.0.0.1:4076
   SHARE_PUBLIC_BASE=https://sea.mom
   ENV
   ```

3. **Install share-service dependencies**
   ```bash
   npm install --prefix share-service
   ```

4. **Launch locally**
   ```bash
   source .venv/bin/activate
   streamlit run sea_airdrop_dashboard.py
   ```

5. **Start the share-card service (optional but recommended)**
   ```bash
   npm run start --prefix share-service
   ```

6. **PM2 supervision (optional)**
   ```bash
   pm2 start ecosystem.config.js
   pm2 save
   ```

## How It Works
Sea Mom orchestrates a Streamlit front-end with cached calls to Dune and a Node render service.

```mermaid
flowchart LR
    A[Streamlit UI] -->|fetch wallet| B{{Dune API}}
    A -->|renders| C[Reveal timeline]
    A -->|posts payload| D[Share Service (Express + canvas)]
    D -->|stores| E[/share/<id> PNG + HTML/]
    B -. joins .-> F[Percentile distributions JSON]
    F --> A
    A --> G[PM2]
```

- **Wallet lookup** hits Dune for summary + per-collection rows, caches results for 5 minutes, and auto-infers percentile bands.
- **Scenario engine** recomputes three cohort cards, heatmaps, and share tables based on global levers (OG pool %, FDV, percentile band).
- **Reveal timeline** narrates the math, drops a hero banner with live numbers, and prefetches the share card.
- **Share service** receives a JSON payload and returns signed URLs to PNG + HTML flex pages.

## Workflows
### 1. Quick wallet projection
- **Command:** `streamlit run sea_airdrop_dashboard.py`
- **Steps:** paste wallet → Fetch History → adjust assumptions → Estimate my airdrop
- **Outcome:** cinematic reveal, share card, percentile curve, fee profile, collections table.

### 2. Iterate on cohort assumptions
- Change the “Scenario cohort size” slider → watch all three scenario cards update.
- Percentile sparklines + highlight point track your wallet across cohorts.

### 3. Share the flex
- Generate reveal → Sea Mom auto-creates the flex card.
- Copy link or click “Tweet this flex” to open a prefilled tweet with the share URL.
- Each card lives under `/share/<slug>` served by the Node microservice.

### 4. Operate in production
- Run both apps under PM2 (`sea-mom`, `sea-mom-share`).
- Configure `BASE_URL`, `APP_PUBLIC_BASE`, and `SHARE_PUBLIC_BASE` so share links use HTTPS.
- Front `streamlit` and `/share` with Nginx for TLS and caching.

## Configuration Cheat Sheet
| Setting | Default | Purpose | Change when |
| --- | --- | --- | --- |
| `DUNE_API_KEY` | – | Auth token for Dune API | Using a different Dune account |
| `DEMO_WALLET` | empty | Prefills the wallet text box | Want a curated example |
| `BASE_URL` | – | Primary public domain | Deploying beyond localhost |
| `APP_PUBLIC_BASE` | inherits `BASE_URL` | Streamlit share links | Serving app and share cards from different domains |
| `SHARE_SERVICE_URL` | `http://127.0.0.1:4076` | Internal Node endpoint | Running share service elsewhere |
| `SHARE_PUBLIC_BASE` | inherits `BASE_URL` | Public share URLs | CDN or alternate subdomain |
| `DEFAULT_REVEAL_DURATION` | `6` | Seconds for reveal timeline | Adjust pacing |
| `TOTAL_SUPPLY` | `1_000_000_000` | Hardcoded SEA supply | Modelling different supply |

## Data & Security
- **Dune rate limits:** caching reduces load; consider rotating API keys for heavy traffic.
- **Secrets:** `.env` is read by both Streamlit and the share service (via `dotenv`). Keep it out of git—`.gitignore` already covers it.
- **Persistence:** share cards are ephemeral files written under `share-service/output/`. Mount a volume or S3 sync if you need durability.
- **Logging:** PM2 captures logs; use `pm2 logs sea-mom --nostream` to view without streaming.

## Troubleshooting & FAQ
- **`StreamlitSecretNotFoundError`:** ensure `.streamlit/secrets.toml` or `.env` contains `BASE_URL`/`SHARE_PUBLIC_BASE` when running in production.
- **Wallet returns “Unknown collection”:** confirm Dune query 5850749 is up to date; restart after updating JSON schema.
- **Share card 500s:** verify the share service is running (`pm2 status`), and check Dune payload fields match the expected keys.
- **Reveal reruns immediately:** Streamlit reruns the script by design; we cache wallet fetches and share cards to prevent spinner loops.
- **Port conflicts:** default share service runs on `4076`; override with `PORT` env if required.

## Share Service
Located under `share-service/` (Express + canvas).
- `npm run dev` – watch mode with auto-reload.
- `npm run start` – production start.
- `npm test` – placeholder for visual regression tests (add snapshots as needed).
- Output files land in `share-service/output/` with metadata JSON.

### PM2 ecosystem
`ecosystem.config.js` defines two processes:
- `sea-mom` – Streamlit app (`.venv/bin/streamlit run sea_airdrop_dashboard.py`).
- `sea-mom-share` – Node share service (`node share-service/src/server.js`).

Run `pm2 start ecosystem.config.js && pm2 save` once, then rely on `pm2 resurrect` after reboots.

## Roadmap
- Add ETH price backtesting to show “then vs now” USD value of historical volume.
- Expand share cards with badge variants (e.g., Super OG vs Cousin) and animated reveal GIFs.
- Integrate percentile distributions directly from Dune APIs to reduce manual JSON updates.
- Add automated smoke tests for reveal flow and share-card generation.

## License
MIT. Pull requests welcome—open an issue if you want to collaborate on new features, styling, or data sources.
