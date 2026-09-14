#!/usr/bin/env python3
"""Scrape specific ASINs from Amazon.in and save as seed data.

Usage: python -m scrapers.scrape_asins B0XXXXXXXXX B0YYYYYYYYY ...
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.amazon_movers_spider import SeedAsinsSpider
from scrapers.base import run_spider


def scrape_asins(asins: list[str]) -> None:
    items = run_spider(SeedAsinsSpider, max_products=len(asins), extra={"asins": asins})

    seed_file = Path(__file__).parent / "seed_asins.json"
    if seed_file.exists():
        with open(seed_file) as handle:
            seed_data = json.load(handle)
    else:
        seed_data = {"amazon_movers": {"description": "Real ASINs from Amazon.in Movers & Shakers", "asins": []}}

    scraped_asins = [item["asin"] for item in items]
    existing = set(seed_data["amazon_movers"]["asins"])
    new_asins = [asin for asin in scraped_asins if asin not in existing]
    seed_data["amazon_movers"]["asins"].extend(new_asins)

    with open(seed_file, "w") as handle:
        json.dump(seed_data, handle, indent=2)

    data_file = Path(__file__).parent / "data" / "amazon_movers_raw.json"
    data_file.parent.mkdir(exist_ok=True)
    with open(data_file, "w", encoding="utf-8") as handle:
        json.dump(items, handle, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(new_asins)} new ASINs to seed_asins.json")
    print(f"Saved {len(items)} products to data/amazon_movers_raw.json")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape individual Amazon ASINs")
    parser.add_argument("asins", nargs="+", help="One or more ASINs to scrape (e.g. B0C9JX7KQ5 B0BV7L9J2M)")
    args = parser.parse_args()
    scrape_asins(args.asins)