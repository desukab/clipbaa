import pytest

from scrapers.config import Settings
from scrapers.io import atomic_write_json
from scrapers.matching.matcher import DeodapMatcher, MatchSummary, run_matching
from scrapers.matching.scoring import opportunity_score

CATALOG = [
    {"sku": "SKU1", "title": "Silicone Stretch Lids Set of 12 Reusable Food Covers",
     "cost_price": 65.0, "mrp": 299.0, "moq": 10, "stock": 200, "weight_g": 180,
     "dimensions_cm": "25x20x5", "white_label": True, "gst_compliant": True,
     "images": [], "description": "", "product_url": "https://d.in/p/1"},
]

AMZ = [{"source": "amazon", "asin": "B1",
        "title": "Silicone Stretch Lids Set of 12 Reusable Food Covers",
        "current_price": 199.0, "mrp": 499.0, "review_count": 23, "rating": 4.2,
        "movers_rank": 3, "bsr_current": 1250, "bsr_30d_avg": 1500,
        "seller_count": 3, "fba_seller_count": 1, "product_url": "https://a.in/dp/B1"}]


def test_run_matching_empty_dir(tmp_path):
    summary = run_matching(Settings(output_dir=str(tmp_path)))
    assert isinstance(summary, MatchSummary)
    assert summary.marketplace_total == 0
    assert summary.winners == []


def test_run_matching_finds_candidate(tmp_path):
    atomic_write_json(tmp_path / "deodap_catalog_raw.json", CATALOG)
    atomic_write_json(tmp_path / "amazon_movers_raw.json", AMZ)
    settings = Settings(output_dir=str(tmp_path), min_confidence=0.4,
                        min_absolute_margin=0.0, min_margin_pct=0.0,
                        min_ticket_price=100.0)
    summary = run_matching(settings)
    assert summary.marketplace_total == 1
    assert len(summary.candidates) == 1
    c = summary.candidates[0]
    assert c.marketplace_asin == "B1"
    assert c.deodap_sku == "SKU1"
    assert c.match_confidence > 0.5
    assert summary.high_opportunity >= 0


def test_matcher_filters_by_confidence():
    m = DeodapMatcher(min_confidence=0.9)
    m.deodap_catalog = CATALOG
    matches = m.find_matches([dict(AMZ[0])])
    assert matches  # identical titles clear a 0.9 confidence bar
    assert all(x.match_confidence >= 0.9 for x in matches)


def test_matcher_near_miss_below_confidence():
    m = DeodapMatcher(min_confidence=0.9)
    m.deodap_catalog = CATALOG
    low = dict(AMZ[0])
    low["title"] = "Silicone Stretch Lids Reusable"
    matches = m.find_matches([low])
    assert matches == []
    assert len(m.near_misses) >= 1
    assert all(x.match_confidence < 0.9 for x in m.near_misses)


def test_matcher_does_not_fabricate_bsr_when_missing():
    m = DeodapMatcher(min_confidence=0.5)
    m.deodap_catalog = CATALOG
    no_bsr = dict(AMZ[0])
    no_bsr.pop("bsr_current")
    no_bsr.pop("bsr_30d_avg")
    rec = m.find_matches([no_bsr])[0]
    assert rec.bsr_current is None
    expected = opportunity_score(
        rec.movers_rank or 999, rec.marketplace_reviews, None, None, rec.roi_pct
    )
    assert rec.opportunity_score == pytest.approx(expected, abs=0.1)


def test_matcher_uses_real_bsr_velocity_when_present():
    m = DeodapMatcher(min_confidence=0.5)
    m.deodap_catalog = CATALOG
    rec = m.find_matches([dict(AMZ[0])])[0]
    assert rec.bsr_current == 1250
    expected = opportunity_score(
        rec.movers_rank or 999, rec.marketplace_reviews, 1500.0, 1250.0, rec.roi_pct
    )
    assert rec.opportunity_score == pytest.approx(expected, abs=0.1)


def test_matcher_unknown_marketplace_has_no_margin():
    m = DeodapMatcher(min_confidence=0.5)
    m.deodap_catalog = CATALOG
    other = dict(AMZ[0])
    other["source"] = "meesho"
    rec = m.find_matches([other])[0]
    assert rec.net_margin_inr is None
    assert rec.roi_pct is None


def test_winners_require_known_fee_model():
    m = DeodapMatcher(min_confidence=0.5)
    m.deodap_catalog = CATALOG
    unknown = dict(AMZ[0])
    unknown["source"] = "meesho"
    known = dict(AMZ[0])
    known["source"] = "amazon"
    winners = m.filter_winners(
        m.find_matches([unknown, known]),
        min_absolute_margin=0.0,
        min_margin_pct=0.0,
        min_ticket_price=0.0,
    )
    assert len(winners) == 1
    assert winners[0].marketplace == "amazon"
