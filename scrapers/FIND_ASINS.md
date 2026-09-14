# Finding Real ASINs for Amazon.in

## Quick Method: Browser DevTools

1. Go to https://www.amazon.in/gp/movers-and-shakers
2. Open DevTools (F12) → Network tab
3. Refresh page
4. Look for XHR/fetch requests to `movers-and-shakers` or similar
5. Or inspect product elements → look for `data-asin="B0XXXXXXXX"`

## Manual Search Method

Search Amazon.in for popular categories and note ASINs from URLs:
- `https://www.amazon.in/dp/B0XXXXXXXX` → ASIN is `B0XXXXXXXX`

## Categories to Search

| Category | Search Terms | Expected ASIN Pattern |
|----------|--------------|----------------------|
| Kitchen | "silicone stretch lids", "garlic press", "herb scissors" | B0xxxxxxxx |
| Electronics | "magnetic cable clips", "monitor light bar", "phone stand" | B0xxxxxxxx |
| Beauty | "gua sha", "blackhead remover", "facial roller" | B0xxxxxxxx |
| Home | "drawer dividers", "packing cubes", "tension rods" | B0xxxxxxxx |
| Pet | "dog lick mat", "slow feeder" | B0xxxxxxxx |

## Add to seed_asins.json

Edit `/workspaces/clipbaa/scrapers/seed_asins.json`:
```json
{
  "amazon_movers": {
    "asins": ["B0REAL12345", "B0REAL67890", ...]
  }
}
```

## Then Run Pipeline

```bash
python -m scrapers.pipeline --live
```

This will use your seed ASINs instead of mock data.

## Scrape & Save New ASINs

```bash
python -m scrapers.scrape_asins B0REAL12345 B0REAL67890
```

This scrapes product details and saves to both seed_asins.json and data/amazon_movers_raw.json.