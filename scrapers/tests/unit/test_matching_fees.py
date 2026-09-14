"""F6 regression: fee math must be marketplace-specific and never fabricated."""
import pytest

from scrapers.matching.fees import FEE_MODELS, get_fee_model


def test_amazon_fee_total_matches_documented_model():
    model = get_fee_model("amazon")
    assert model is not None
    assert model.fee_total(199.0, 180) == pytest.approx(29.85 + 5 + 16 + 3.78, abs=0.01)
    assert model.fee_total(600.0, 300) == pytest.approx(90 + 10 + 22 + (10 + 22) * 0.18, abs=0.01)


def test_fee_total_uses_tier_rollover():
    model = get_fee_model("amazon")
    assert model.closing_fee(100.0) == 5
    assert model.closing_fee(600.0) == 10
    assert model.shipping_fee(180) == 16
    assert model.shipping_fee(300) == 22
    assert model.shipping_fee(700) == 35


def test_get_fee_model_unknown_is_none():
    assert get_fee_model("meesho") is None
    assert get_fee_model("flipkart") is None
    assert get_fee_model("deodap") is None
    assert get_fee_model("nope") is None


def test_registered_models_are_explicit_only():
    assert set(FEE_MODELS) <= {"amazon"}
