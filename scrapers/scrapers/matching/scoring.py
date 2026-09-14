"""Pure scoring, similarity, and margin math for the matcher (stdlib only)."""
import re
from difflib import SequenceMatcher
from typing import Dict, Optional, Tuple

from scrapers.matching.fees import MarketplaceFeeModel

NEAR_MISS_FLOOR = 0.35

NOISE_PATTERNS = [
    r"\btoy",
    r"novelty",
    r"party",
    r"costume",
    r"plush",
    r"balloon",
    r"\bgame\b",
    r"carnival",
    r"school",
    r"stationery",
    r"students?",
    r"kids",
    r"children",
    r"perfume",
    r"air\s*freshener",
    r"fridge magnet",
    r"key\s*chain",
    r"crackers?",
    r"fireworks?",
    r"costume jewellery",
]

HIGH_UTILITY_KEYWORDS = [
    "storage", "organi", "container", "bottle", "tumbler", "flask",
    "carafe", "kettle", "cookware", "pan", "knife", "kitchen", "stainless",
    "jar", "coffee", "tea", "rack", "shelf", "bin", "dry", "airtight",
    "insulat", "vacuum",
]

_STOPWORDS = {
    "set", "pack", "piece", "pcs", "pc", "kit", "combo", "value", "premium", "pro", "new", "latest",
    "amazon", "basics", "brand", "presto", "shalimar", "jialto", "milton", "wakefit", "nutripro",
    "godrej", "trance", "daluci", "bisleri", "ezee", "homestrap", "nova", "zulaxy", "agaro",
    "desidiya", "aerys", "one94store", "aeros", "fancymart", "limetro", "solimo", "garbage",
    "bottle", "water", "heavy", "duty", "self", "adhesive", "free", "indian", "india", "best",
    "stainless", "steel", "made",
}


def to_float(value) -> float:
    """Robustly coerce a field to float, treating None/blank as 0.0."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    words = []
    for w in title.split():
        if w in _STOPWORDS or len(w) <= 2:
            continue
        words.append(w)
    return " ".join(words)


def similarity(a: str, b: str) -> float:
    na = normalize_title(a)
    nb = normalize_title(b)
    tokens_a = set(na.split())
    tokens_b = set(nb.split())
    if not tokens_a or not tokens_b:
        return 0.0
    shared = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    jaccard = shared / union if union else 0.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    return 0.6 * jaccard + 0.4 * ratio


def calculate_margin(
    marketplace_price: float,
    deodap_cost: float,
    weight_g: int,
    fee_model: Optional[MarketplaceFeeModel] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """Net margin and accounting ROI after fees + GST using landed cost.

    Returns ``(None, None)`` (``INSUFFICIENT_DATA``) when the marketplace has no
    registered fee model; fees are never assumed for unknown marketplaces.
    """
    if fee_model is None:
        return None, None
    fee_total = fee_model.fee_total(marketplace_price, weight_g)
    if fee_total is None:
        return None, None
    landed_cost = (
        deodap_cost * (1 + fee_model.gst_rate) if fee_model.gst_rate is not None else deodap_cost
    )

    net_margin = marketplace_price - fee_total - landed_cost
    roi = (net_margin / landed_cost) * 100 if landed_cost > 0 else 0

    return net_margin, roi


def competition_score(review_count: int) -> int:
    if 10 <= review_count <= 50:
        return 100
    if review_count < 10:
        return 80
    if review_count <= 100:
        return 60
    return 20


def velocity_score(bsr_avg: Optional[float], bsr_current: Optional[float]) -> Optional[float]:
    """Demand velocity from BSR trend. None = INSUFFICIENT_DATA (not fabricable).

    Requires a real 30-day average AND a real current rank; a missing or
    non-positive value on either side means there is no honest signal.
    """
    if bsr_avg is None or bsr_current is None:
        return None
    if bsr_avg <= 0 or bsr_current <= 0:
        return None
    return max(0.0, min(100.0, ((bsr_avg - bsr_current) / bsr_avg) * 100))


def opportunity_score(
    movers_rank: int,
    review_count: int,
    bsr_avg: Optional[float],
    bsr_current: Optional[float],
    roi: Optional[float],
) -> float:
    movers_score = max(0, 101 - (movers_rank or 999))
    comp_score = competition_score(review_count)
    vel = velocity_score(bsr_avg, bsr_current)
    roi_score = min(100.0, roi / 2) if roi is not None else None
    terms = [(movers_score, 0.30), (comp_score, 0.30)]
    weights_sum = 0.60
    if vel is not None:
        terms.append((vel, 0.20))
        weights_sum += 0.20
    if roi_score is not None:
        terms.append((roi_score, 0.20))
        weights_sum += 0.20
    return sum(score * (w / weights_sum) for score, w in terms)


def is_noise(title: str) -> bool:
    """Flag low-value novelty/toy/novelty clutter by keyword pattern."""
    return any(re.search(p, title, re.IGNORECASE) for p in NOISE_PATTERNS)


def utility_bonus(title: str) -> int:
    """Count high-utility keywords (storage/drinkware/kitchen) for prioritization."""
    t = title.lower()
    return sum(1 for kw in HIGH_UTILITY_KEYWORDS if kw in t)


def eligible_deodap(dp: Dict, mp_price: float) -> bool:
    if not dp.get("white_label") or not dp.get("gst_compliant"):
        return False
    if dp.get("stock", 0) < 20:
        return False
    if to_float(dp.get("weight_g", 999)) > 500:
        return False
    if to_float(dp.get("cost_price")) * 1.18 >= mp_price:
        return False
    return True
