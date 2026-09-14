import pytest

from scrapers.matching.fees import get_fee_model
from scrapers.matching.scoring import (
    calculate_margin,
    competition_score,
    eligible_deodap,
    is_noise,
    normalize_title,
    opportunity_score,
    similarity,
    to_float,
    utility_bonus,
    velocity_score,
)


def test_margin_tier_1():
    net, roi = calculate_margin(199.0, 65.0, 180, get_fee_model("amazon"))
    expected_net = 199 - 29.85 - 5 - 16 - 3.78 - (65 * 1.18)
    assert net == pytest.approx(expected_net, abs=0.01)
    assert roi == pytest.approx((expected_net / (65 * 1.18)) * 100, abs=0.1)


def test_margin_fee_tiers():
    n2, r2 = calculate_margin(600.0, 200.0, 300, get_fee_model("amazon"))
    n3, r3 = calculate_margin(1200.0, 300.0, 600, get_fee_model("amazon"))
    assert n2 < n3
    assert r2 > 0 and r3 > 0


def test_margin_unknown_marketplace_is_insufficient_data():
    net, roi = calculate_margin(199.0, 65.0, 180, None)
    assert net is None and roi is None
    net2, roi2 = calculate_margin(199.0, 65.0, 180, get_fee_model("meesho"))
    assert net2 is None and roi2 is None


def test_competition_tiers():
    assert competition_score(5) == 80
    assert competition_score(30) == 100
    assert competition_score(60) == 60
    assert competition_score(500) == 20


def test_velocity():
    assert velocity_score(2000, 1000) == 50.0
    assert velocity_score(0, 1000) is None


def test_velocity_insufficient_data_is_none():
    assert velocity_score(None, None) is None
    assert velocity_score(2000, None) is None
    assert velocity_score(None, 1000) is None
    assert velocity_score(2000, 0) is None


def test_opportunity():
    score = opportunity_score(1, 30, 2000, 1000, 100)
    assert score == pytest.approx(100 * 0.3 + 100 * 0.3 + 50 * 0.2 + 50 * 0.2, abs=0.01)


def test_opportunity_no_velocity_data():
    score = opportunity_score(1, 30, None, None, 100)
    assert score == pytest.approx(100 * 0.375 + 100 * 0.375 + 50 * 0.25, abs=0.01)


def test_opportunity_no_roi_or_velocity_data():
    score = opportunity_score(1, 30, None, None, None)
    assert score == pytest.approx(100 * 0.5 + 100 * 0.5, abs=0.01)


def test_similarity_normalized():
    a = "Silicone Stretch Lids Set of 12 - Reusable Food Covers"
    b = "Silicone Stretch Lids 12 Pcs - Reusable Food Covers"
    assert similarity(a, b) > 0.4


def test_noise_and_utility():
    assert is_noise("Kids Party Fancy Dress Costume Toy")
    assert not is_noise("Stainless Steel Kitchen Storage Container")
    assert utility_bonus("Airtight Stainless Steel Kitchen Storage Container") >= 2


def test_eligible_deodap():
    ok = {
        "white_label": True,
        "gst_compliant": True,
        "stock": 50,
        "weight_g": 300,
        "cost_price": 100,
    }
    assert eligible_deodap(ok, 500)
    assert not eligible_deodap({**ok, "white_label": False}, 500)
    assert not eligible_deodap({**ok, "stock": 5}, 500)
    assert not eligible_deodap({**ok, "weight_g": 900}, 500)
    assert not eligible_deodap({**ok, "cost_price": 500}, 500)


def test_to_float_and_normalize():
    assert to_float("12.5") == 12.5
    assert to_float(None) == 0.0
    assert normalize_title("Silicone Lids Set of 12") == "silicone lids"
