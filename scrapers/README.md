# Scrapling E-Commerce Pipeline - India

Robust market-research scrapers for Amazon India Movers & Shakers, Meesho Trending, Flipkart Bestsellers, and DeoDap, built on the Scrapling Spider framework.

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
pip install -r requirements.txt
# Install browser binaries used by the stealth/dynamic sessions (Amazon, Flipkart, Meesho):
scrapling install
```

## Quick Start

```bash
# Mock mode (offline, uses bundled sample data + runs the matcher):
python -m scrapers.pipeline

# Live scrape all sources + cross-reference:
python -m scrapers.pipeline --live

# Or run individual spiders:
python -m scrapers.amazon_movers_spider --live
python -m scrapers.meesho_trending_spider --live
python -m scrapers.flipkart_bestsellers_spider --live
python -m scrapers.deodap_catalog_spider --live

# Just matching (after you have raw data):
python -m scrapers.matcher
```

## Workflow: the adaptive selector loop

1. **First live run (default):** parsers save DOM fingerprints for every registered
   field into the adaptive store (`.scrapling/`).
2. **After a site changes its markup:** rerun with
   `SCRAPLING_ADAPTIVE=1 python -m scrapers.pipeline --live`. Fields are relocated
   from the saved fingerprints instead of the stale hard-coded selectors.

## Environment variables

| Variable | Effect |
|----------|--------|
| `SCRAPLING_ADAPTIVE=1` | Enable adaptive relocation; unset = training (`auto_save`) mode |
| `SCRAPLING_CRAWL_DIR=./crawls` | Enable checkpoint-based pause/resume for spiders |
| `SCRAPLING_PROXY=http://user:pass@host:port` | Route all sessions through a proxy (or a `ProxyRotator`) |
| `FLIPKART_BESTSELLERS_URL` | Override the bestsellers entry URL |
| `MEESHO_TRENDING_URL` | Override the trending entry URL |
| `DEODAP_BASE_URL` | Override the DeoDap store base URL |
| `DEODAP_CATEGORIES` | Comma-separated category slugs (defaults built in) |

## Output Files

| File | Description |
|------|-------------|
| `data/amazon_movers_raw.json` | Raw Amazon Movers & Shakers products |
| `data/meesho_trending_raw.json` | Raw Meesho trending products |
| `data/flipkart_bestsellers_raw.json` | Raw Flipkart bestsellers |
| `data/deodap_catalog_raw.json` | DeoDap wholesale catalog |
| `data/matched_products.json` | Cross-referenced matches with scoring |
| `data/matched_products.csv` | Excel/Sheets ready format |

## Matching Algorithm

Products are matched on title similarity (fuzzy) + filtered by:
- DeoDap white-label + GST compliant
- Stock ≥ 20 units
- Weight ≤ 500g
- Cost price < Amazon selling price (after fees)

## Opportunity Scoring (0-100)

```
Movers Rank (30%) + Competition (30%) + Velocity (20%) + ROI (20%)

Movers Rank: 101 - rank (rank 1 = 100, rank 50 = 51)
Competition: 10 reviews=80, 10-50 reviews=100, 50-100=60, 100+=20
Velocity: % BSR drop over 30 days
ROI: min(100, roi%/2)
```

## Thresholds for Action

| Metric | Minimum |
|--------|---------|
| Opportunity Score | ≥ 65 |
| Match Confidence | ≥ 65% |
| Net Margin | ≥ ₹40 |
| ROI | ≥ 50% |
| Review Count | 10-50 |
| Movers Rank | ≤ 50 |
| Seller Count | ≤ 5 |
| FBA Sellers | ≤ 2 |

## Legal Compliance

- Scrapes public pages only
- No authentication bypass
- AutoThrottle + per-domain delays keep request rates polite
- For research/personal use — check each marketplace's ToS before commercial use