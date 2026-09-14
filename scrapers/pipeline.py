#!/usr/bin/env python3
"""Full Pipeline Orchestrator

Run: python -m scrapers.pipeline [--live] [--mock]

Robustness notes:
- Live mode runs every marketplace crawler as a Scrapling Spider (concurrency,
  AutoThrottle, retries, blocked-request detection, pause/resume with
  SCRAPLING_CRAWL_DIR). Zero fabricated data: if a crawl produces no items it
  is reported loudly instead of being silently replaced by mocks.
- Mock mode (default) writes the bundled sample catalog so offline work on the
  matcher and reporting pipeline stays possible.
- SCRAPLING_ADAPTIVE=1 makes the parsers relocate fields registered on earlier
  runs instead of relying on the hard-coded selectors (run once without it to
  train the adaptive store).
"""
import argparse
import sys
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.amazon_movers_spider import (
    MOCK_AMAZON_MOVERS,
    AmazonMoversSpider,
)
from scrapers.meesho_trending_spider import (
    MOCK_MEESHO_TRENDING,
    MeeshoSpider,
)
from scrapers.flipkart_bestsellers_spider import (
    MOCK_FLIPKART_BESTSELLERS,
    FlipkartSpider,
)
from scrapers.deodap_catalog_spider import (
    MOCK_DEODAP_CATALOG,
    DeodapSpider,
)
from scrapers.base import run_spider, write_items
from scrapers.matcher import run_matching_pipeline


def run_full_pipeline(use_live: bool = False):
    Path("data").mkdir(exist_ok=True)

    print("=" * 60)
    print("SCRAPLING E-COMMERCE PIPELINE - INDIA")
    print(f"Mode: {'LIVE scraping' if use_live else 'MOCK data'}")
    print("=" * 60)

    if use_live:
        print("\n[1/5] Scraping Amazon India Movers & Shakers...")
        write_items(run_spider(AmazonMoversSpider, max_products=50), "data/amazon_movers_raw.json")

        print("\n[2/5] Scraping Meesho Trending...")
        write_items(run_spider(MeeshoSpider, max_products=30), "data/meesho_trending_raw.json")

        print("\n[3/5] Scraping Flipkart Bestsellers...")
        write_items(run_spider(FlipkartSpider, max_products=25), "data/flipkart_bestsellers_raw.json")

        print("\n[4/5] Generating DeoDap Catalog...")
        write_items(run_spider(DeodapSpider, max_products=0), "data/deodap_catalog_raw.json")
    else:
        print("\n[1/5] Using mock Amazon products...")
        write_items([asdict(p) for p in MOCK_AMAZON_MOVERS], "data/amazon_movers_raw.json")

        print("\n[2/5] Using mock Meesho products...")
        write_items([asdict(p) for p in MOCK_MEESHO_TRENDING], "data/meesho_trending_raw.json")

        print("\n[3/5] Using mock Flipkart products...")
        write_items([asdict(p) for p in MOCK_FLIPKART_BESTSELLERS], "data/flipkart_bestsellers_raw.json")

        print("\n[4/5] Using mock DeoDap catalog...")
        write_items([asdict(p) for p in MOCK_DEODAP_CATALOG], "data/deodap_catalog_raw.json")

    print("\n[5/5] Cross-referencing & Scoring...")
    matches = run_matching_pipeline()

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print("\nOutput files:")
    print("  - data/matched_products.json (full data)")
    print("  - data/matched_products.csv (for Excel/Sheets)")
    print("\nNext steps:")
    print("  1. Review top 10 in CSV")
    print("  2. Validate DeoDap stock manually")
    print("  3. Create Amazon listings for top 3-5")
    print("  4. Order test inventory (MOQ) from DeoDap")

    return matches


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrapling E-Commerce Pipeline")
    parser.add_argument("--live", action="store_true", help="Use live scraping (default: mock data)")
    parser.add_argument("--mock", action="store_true", help="Use mock data (default)")
    args = parser.parse_args()

    use_live = args.live and not args.mock
    run_full_pipeline(use_live=use_live)