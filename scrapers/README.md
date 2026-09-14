# Scrapling E-Commerce Pipeline - India

Market-research scrapers for Amazon India Movers & Shakers / Bestsellers, Meesho Trending,
Flipkart Bestsellers, and the DeoDap wholesale catalog, built on the Scrapling Spider
framework. Crawled listings are cross-referenced against the DeoDap catalog and ranked for
resale opportunity.

Every source is a `scrapling.spiders.Spider` subclass with:

- Native concurrency (no per-request event-loop hacks)
- AutoThrottle — per-domain delays that back off when a site blocks or rate-limits you
- Blocked-request detection + automatic retries
- Correct fetcher per site:
  - Amazon / Flipkart → `AsyncStealthySession` (bot-wall + Turnstile bypass)
  - Meesho → `AsyncDynamicSession` (SPA requires a real browser + network idle)
  - DeoDap → `FetcherSession` (fast TLS-impersonated HTTP)
- Adaptive selectors — run once to register fingerprints, then re-run with `SCRAPLING_ADAPTIVE=1` after a site redesign to auto-relocate fields
- Optional pause/resume checkpoints and proxy support
- No silent mock fallback in live mode — a failed crawl is reported, never fabricated

## Installation

```bash
cd scrapers
pip install -e ".[dev]"          # pytest + flake8 for local development
pip install -e ".[fetchers]"     # PLUS live scraping (scrapling[fetchers]) on a glibc host
scrapling install                # browser binaries for stealth/dynamic sessions
```

Live scraping requires `scrapling[fetchers]` on a glibc host (e.g. proot-Distro Ubuntu).
Without it the package still imports and runs in mock mode; live commands fail with exit
code 4 and a clear install message.

## CLI

The console script is `pipeline` (`python -m scrapers.cli` works too):

```bash
# Mock mode (offline, bundled sample data + matcher + reports):
pipeline run --mock

# Live scrape all sources + match + reports:
pipeline run --live

# Limit sources / products:
pipeline run --live --sources amazon,deodap --max-products 25

# Match against already-crawled raw data only:
pipeline match

# Show/filter price-history velocity + alerts:
pipeline history

# Reports / optional exports from existing raw data:
pipeline export --sheets --webhook

# Inspect registered sources / validate configuration:
pipeline list-sources
pipeline validate-config

# Scrape specific Amazon ASINs (live) and record them in seed_asins.json:
pipeline scrape-asins B0REAL12345 B0REAL67890
pipeline scrape-asins            # uses the ASINs already in seed_asins.json
```

Global flags: `--env-file PATH` and `--output-dir PATH` (override `OUTPUT_DIR`).
Run artifacts land in `data/runs/<run-id>/manifest.json` + `run.log`.

## Workflow: the adaptive selector loop

1. **First live run (default):** parsers save DOM fingerprints for every registered
   field into the adaptive store (`.scrapling/`).
2. **After a site changes its markup:** rerun with
   `SCRAPLING_ADAPTIVE=1 pipeline run --live`. Fields are relocated from the saved
   fingerprints instead of the stale hard-coded selectors.

## Environment variables

| Variable | Effect |
|----------|--------|
| `LOG_LEVEL` / `LOG_FORMAT` | Logging verbosity (`DEBUG`-`CRITICAL`); `console` or `json` |
| `OUTPUT_DIR` | Where raw/match/report files are written (default `data`) |
| `SCRAPLING_ADAPTIVE=1` | Enable adaptive relocation; unset = training (`auto_save`) mode |
| `SCRAPLING_ADAPTIVE_PERCENTAGE` | Portion of requests routed to fingerprint saving (default 40) |
| `SCRAPLING_CRAWL_DIR=./crawls` | Enable checkpoint-based pause/resume for spiders |
| `SCRAPLING_PROXY=http://user:pass@host:port` | Route all sessions through a proxy |
| `AMAZON_MOVERS_URL` / `AMAZON_BESTSELLERS_URLS` | Amazon entry URLs (bestsellers are comma-separated) |
| `MEESHO_TRENDING_URL` / `FLIPKART_BESTSELLERS_URL` | Meesho/Flipkart entry URLs |
| `DEODAP_BASE_URL` / `DEODAP_CATEGORIES` | DeoDap store base URL + category slugs |
| `MIN_CONFIDENCE` | Match-confidence bar (default `0.5`) |
| `MIN_TICKET_PRICE` | Minimum Amazon selling price (default `300`) |
| `MIN_ABSOLUTE_MARGIN` / `MIN_MARGIN_PCT` | Winner margin bars (default `200` / `35`) |
| `MAX_SELLERS` / `MAX_FBA_SELLERS` | Competition gates (default `5` / `2`) |
| `REPORT_TOP_N` | Winners shown in `winners.md` (default `25`) |
| `SHEETS_SERVICE_ACCOUNT` / `SHEETS_SPREADSHEET_ID` | Google Sheets export |
| `WEBHOOK_URL` / `WEBHOOK_SECRET` | Match webhook export |

## Output Files

| File | Description |
|------|-------------|
| `data/amazon_movers_raw.json` | Raw Amazon Movers & Shakers / Bestsellers products |
| `data/meesho_trending_raw.json` | Raw Meesho trending products |
| `data/flipkart_bestsellers_raw.json` | Raw Flipkart bestsellers |
| `data/deodap_catalog_raw.json` | DeoDap wholesale catalog |
| `data/matched_products.json` | All scored candidates / winners / near-misses, with margin + opportunity |
| `data/matched_products.csv` | Sheets-ready winner rows (title, SKU, cost, price, margin) |
| `data/winners.md` | Ranked winner report |
| `data/near_matches.json` | Near-miss matches below the confidence bar |
| `data/runs/<run-id>/` | Per-run manifest + log |

## Matching Algorithm

Products are matched on title similarity (fuzzy), then filtered by:
- DeoDap white-label + GST compliant
- Stock ≥ 20 units, weight ≤ 500g
- Cost price < marketplace selling price
- Match confidence ≥ `MIN_CONFIDENCE`

Winners must additionally clear the margin/competition gates above *and* have a
registered fee model so net margin can actually be computed.

## Fees and Margins (honest by default)

Net-margin math uses a per-marketplace fee model (`scrapers/matching/fees.py`). Only
marketplaces with a researched fee schedule are registered:

- **Amazon:** referral 15%, closing ₹5 ≤₹250 / ₹10 above, shipping ₹16 / ₹22 / ₹35 by
  weight bracket, GST 18% on fees and landed cost.
- **Meesho / Flipkart / DeoDap:** no registered fee model → net margin is
  `INSUFFICIENT_DATA` (`None`) and such candidates can never become winners. Fees are
  never assumed for unknown marketplaces.

Registering a new model is a one-line dict entry in `fees.py`.

## Opportunity Scoring (0-100)

```
Movers Rank (30%) + Competition (30%) + Velocity (20%) + ROI (20%)

Movers Rank:  101 - rank (rank 1 = 100, rank 50 = 51)
Competition:  <10 reviews=80, 10-50=100, 50-100=60, 100+=20
Velocity:     % BSR drop vs the 30-day BSR average (None when BSR data is missing)
ROI:          min(100, roi%/2)

When velocity and/or ROI are unknown the remaining weights are renormalized
(0-100 scale is preserved); the score reflects only signals that actually exist.
```

Marketplace demand velocity requires both a real 30-day BSR average and a real current
BSR rank. Missing data is `INSUFFICIENT_DATA` (`None`), never a fabricated constant.

## Legal Compliance

- Scrapes public pages only
- No authentication bypass
- AutoThrottle + per-domain delays keep request rates polite
- For research/personal use — check each marketplace's ToS before commercial use