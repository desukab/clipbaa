import json
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from difflib import SequenceMatcher
import pandas as pd

CSV_COLUMNS = [
    "amazon_title",
    "deodap_sku",
    "cost",
    "amazon_price",
    "absolute_margin_inr",
    "margin_percentage",
]

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


def _to_float(value) -> float:
    """Robustly coerce a field to float, treating None/blank as 0.0."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class MatchedProduct:
    marketplace: str
    marketplace_asin: str
    marketplace_title: str
    marketplace_price: float
    marketplace_reviews: int
    marketplace_rating: Optional[float]
    movers_rank: Optional[int]
    bsr_current: Optional[int]
    seller_count: int
    fba_seller_count: int
    weight_g: Optional[int]

    deodap_sku: str
    deodap_title: str
    deodap_cost: float
    deodap_moq: int
    deodap_stock: int
    deodap_weight_g: int
    deodap_white_label: bool
    deodap_gst_compliant: bool

    match_confidence: float
    net_margin_inr: float
    roi_pct: float
    absolute_margin_inr: float
    margin_percentage: float
    opportunity_score: float


class DeodapMatcher:
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence
        self.deodap_catalog: List[Dict] = []
        self.near_misses: List[MatchedProduct] = []

    def load_catalog(self, filepath: str):
        with open(filepath, 'r') as f:
            self.deodap_catalog = json.load(f)
        print(f"Loaded {len(self.deodap_catalog)} DeoDap products")

    def _normalize_title(self, title: str) -> str:
        title = title.lower()
        title = re.sub(r'[^\w\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title).strip()
        stopwords = {
            'set', 'pack', 'piece', 'pcs', 'pc', 'kit', 'combo', 'value', 'premium', 'pro', 'new', 'latest',
            'amazon', 'basics', 'brand', 'presto', 'shalimar', 'jialto', 'milton', 'wakefit', 'nutripro',
            'godrej', 'trance', 'daluci', 'bisleri', 'ezee', 'homestrap', 'nova', 'zulaxy', 'agaro',
            'desidiya', 'aerys', 'one94store', 'aeros', 'fancymart', 'limetro', 'solimo', 'garbage',
            'bottle', 'water', 'heavy', 'duty', 'self', 'adhesive', 'free', 'indian', 'india', 'best',
            'stainless', 'steel', 'made',
        }
        words = []
        for w in title.split():
            if w in stopwords or len(w) <= 2:
                continue
            if w.endswith('s') and len(w) > 3:
                w = w[:-1]
            words.append(w)
        return ' '.join(words)

    def _similarity(self, a: str, b: str) -> float:
        tokens_a = set(self._normalize_title(a).split())
        tokens_b = set(self._normalize_title(b).split())
        if not tokens_a or not tokens_b:
            return 0.0
        shared = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        jaccard = shared / union if union else 0.0
        ratio = SequenceMatcher(
            None, self._normalize_title(a), self._normalize_title(b)
        ).ratio()
        return 0.6 * jaccard + 0.4 * ratio

    def _calculate_margin(self, marketplace_price: float, deodap_cost: float, weight_g: int) -> tuple:
        """Net margin and accounting ROI (after fees + GST using landed cost)."""
        referral_fee = 0
        closing_fee = 5 if marketplace_price <= 250 else 10

        if weight_g <= 200:
            shipping_fee = 16
        elif weight_g <= 500:
            shipping_fee = 22
        else:
            shipping_fee = 35

        gst_on_fees = (closing_fee + shipping_fee) * 0.18
        total_fees = closing_fee + shipping_fee + gst_on_fees
        landed_cost = deodap_cost * 1.18

        net_margin = marketplace_price - total_fees - landed_cost
        roi = (net_margin / landed_cost) * 100 if landed_cost > 0 else 0

        return net_margin, roi

    def _eligible_deodap(self, dp: Dict, mp_price: float) -> bool:
        if not dp.get('white_label') or not dp.get('gst_compliant'):
            return False
        if dp.get('stock', 0) < 20:
            return False
        if _to_float(dp.get('weight_g', 999)) > 500:
            return False
        if _to_float(dp.get('cost_price')) * 1.18 >= mp_price:
            return False
        return True

    def _best_candidate(self, mp_title: str, mp_price: float) -> tuple:
        best_match = None
        best_confidence = 0.0
        for dp in self.deodap_catalog:
            if not self._eligible_deodap(dp, mp_price):
                continue
            confidence = self._similarity(mp_title, dp.get('title', ''))
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = dp
        return best_match, best_confidence

    def find_matches(self, marketplace_products: List[Dict]) -> List[MatchedProduct]:
        matches = []
        self.near_misses = []

        for mp in marketplace_products:
            mp_title = str(mp.get('title') or '')
            mp_price = _to_float(mp.get('current_price'))
            if mp_price <= 0:
                continue

            best_match, best_confidence = self._best_candidate(mp_title, mp_price)
            if not best_match:
                continue

            scored = self._score_match(mp, best_match, best_confidence)
            if best_confidence >= self.min_confidence:
                matches.append(scored)
            elif best_confidence >= NEAR_MISS_FLOOR:
                self.near_misses.append(scored)

        return matches

    def _score_match(self, mp: Dict, best_match: Dict, best_confidence: float) -> MatchedProduct:
        mp_title = str(mp.get('title') or '')
        mp_weight = int(_to_float(mp.get('weight_g')) or 200)
        mp_price = _to_float(mp.get('current_price'))
        cost = _to_float(best_match.get('cost_price'))

        net_margin, roi = self._calculate_margin(mp_price, cost, mp_weight)
        absolute_margin_inr = round(mp_price - cost, 2)
        margin_percentage = round(((mp_price - cost) / cost) * 100, 1) if cost > 0 else 0.0

        movers_rank = mp.get('movers_rank') or 999
        movers_score = max(0, 101 - movers_rank)

        review_count = int(_to_float(mp.get('review_count')))
        if 10 <= review_count <= 50:
            comp_score = 100
        elif review_count < 10:
            comp_score = 80
        elif review_count <= 100:
            comp_score = 60
        else:
            comp_score = 20

        bsr_avg = _to_float(mp.get('bsr_30d_avg')) or (_to_float(mp.get('bsr_current')) or 10000) * 2
        bsr_current = _to_float(mp.get('bsr_current')) or 10000
        velocity_score = max(0, min(100, ((bsr_avg - bsr_current) / bsr_avg) * 100)) if bsr_avg > 0 else 0

        roi_score = min(100, roi / 2)

        opportunity = (
            movers_score * 0.30 +
            comp_score * 0.30 +
            velocity_score * 0.20 +
            roi_score * 0.20
        )

        return MatchedProduct(
            marketplace=mp.get('source', 'unknown'),
            marketplace_asin=mp.get('asin') or mp.get('product_id') or '',
            marketplace_title=mp_title,
            marketplace_price=mp_price,
            marketplace_reviews=review_count,
            marketplace_rating=mp.get('rating'),
            movers_rank=mp.get('movers_rank'),
            bsr_current=bsr_current,
            seller_count=int(_to_float(mp.get('seller_count'))),
            fba_seller_count=int(_to_float(mp.get('fba_seller_count'))),
            weight_g=mp_weight,

            deodap_sku=str(best_match.get('sku', '')),
            deodap_title=str(best_match.get('title', '')),
            deodap_cost=cost,
            deodap_moq=int(_to_float(best_match.get('moq'))),
            deodap_stock=int(_to_float(best_match.get('stock'))),
            deodap_weight_g=int(_to_float(best_match.get('weight_g'))),
            deodap_white_label=bool(best_match.get('white_label')),
            deodap_gst_compliant=bool(best_match.get('gst_compliant')),

            match_confidence=best_confidence,
            net_margin_inr=round(net_margin, 2),
            roi_pct=round(roi, 1),
            absolute_margin_inr=absolute_margin_inr,
            margin_percentage=margin_percentage,
            opportunity_score=round(opportunity, 1)
        )

    def _is_noise(self, title: str) -> bool:
        """Flag low-value novelty/toy/novelty clutter by keyword pattern."""
        return any(re.search(p, title, re.IGNORECASE) for p in NOISE_PATTERNS)

    def _utility_bonus(self, title: str) -> int:
        """Count high-utility keywords (storage/drinkware/kitchen) for prioritization."""
        t = title.lower()
        return sum(1 for kw in HIGH_UTILITY_KEYWORDS if kw in t)

    def filter_winners(
        self,
        candidates: List[MatchedProduct],
        min_absolute_margin: float = 200.0,
        min_margin_pct: float = 35.0,
        min_ticket_price: float = 300.0,
    ) -> List[MatchedProduct]:
        """Discard any pair that fails the profit guardrails or is low-ticket noise."""
        winners = []
        for m in candidates:
            if m.marketplace_price < min_ticket_price:
                continue
            if m.absolute_margin_inr < min_absolute_margin:
                continue
            if m.margin_percentage < min_margin_pct:
                continue
            if self._is_noise(m.marketplace_title):
                continue
            winners.append(m)
        winners.sort(
            key=lambda m: (self._utility_bonus(m.marketplace_title), m.opportunity_score),
            reverse=True,
        )
        return winners


def load_marketplace_products() -> List[Dict]:
    products = []
    for filepath, source in [
        ("data/amazon_movers_raw.json", "amazon"),
        ("data/meesho_trending_raw.json", "meesho"),
        ("data/flipkart_bestsellers_raw.json", "flipkart")
    ]:
        try:
            with open(filepath, 'r') as f:
                batch = json.load(f)
        except FileNotFoundError:
            print(f"File not found: {filepath}")
            continue
        for p in batch:
            p['source'] = source
            if _to_float(p.get('current_price')) > 0:
                products.append(p)
        print(f"Loaded {len(batch)} products from {source}")
    return products


def write_winners_csv(winners: List[MatchedProduct]):
    rows = [{
        "amazon_title": w.marketplace_title,
        "deodap_sku": w.deodap_sku,
        "cost": w.deodap_cost,
        "amazon_price": w.marketplace_price,
        "absolute_margin_inr": w.absolute_margin_inr,
        "margin_percentage": w.margin_percentage,
    } for w in winners]
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    df.to_csv("data/matched_products.csv", index=False)


def run_matching_pipeline(
    min_confidence: float = 0.5,
    min_absolute_margin: float = 200.0,
    min_margin_pct: float = 35.0,
    min_ticket_price: float = 300.0,
):
    matcher = DeodapMatcher(min_confidence=min_confidence)
    matcher.load_catalog("data/deodap_catalog_raw.json")

    all_marketplace_products = load_marketplace_products()
    candidates = matcher.find_matches(all_marketplace_products)
    winners = matcher.filter_winners(
        candidates,
        min_absolute_margin=min_absolute_margin,
        min_margin_pct=min_margin_pct,
        min_ticket_price=min_ticket_price,
    )

    output = [asdict(w) for w in winners]
    with open("data/matched_products.json", "w") as f:
        json.dump(output, f, indent=2)
    write_winners_csv(winners)

    near = [asdict(nm) for nm in matcher.near_misses]
    with open("data/near_matches.json", "w") as f:
        json.dump(near, f, indent=2)

    print(f"\n=== MATCHING RESULTS ===")
    print(f"Total marketplace products: {len(all_marketplace_products)}")
    print(f"Scored candidates (>= {min_confidence:.0%} confidence): {len(candidates)}")
    print(f"High-margin winners: {len(winners)}")
    print(f"High opportunity (>65): {len([w for w in winners if w.opportunity_score >= 65])}")
    print(f"\nQualified Winners ({len(winners)}):")
    for i, w in enumerate(winners, 1):
        print(
            f"  {i}. {w.marketplace_title[:55]}... | {w.deodap_sku[:28]} | "
            f"₹{w.deodap_cost} -> ₹{w.marketplace_price} | ₹{w.absolute_margin_inr} "
            f"| {w.margin_percentage}% | Match: {w.match_confidence:.0%}"
        )
    if matcher.near_misses:
        print(f"\nNear-miss candidates (below {matcher.min_confidence:.0%} confidence, see data/near_matches.json):")
        ranked = sorted(matcher.near_misses, key=lambda m: m.absolute_margin_inr, reverse=True)[:10]
        for nm in ranked:
            print(
                f"  - {nm.marketplace_title[:48]}... ~ {nm.deodap_title[:36]}... | "
                f"Match: {nm.match_confidence:.0%} | ₹{nm.absolute_margin_inr} margin"
            )

    return winners


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Match marketplace listings to DeoDap catalog")
    parser.add_argument("--min-confidence", type=float, default=0.5,
                        help="Minimum title-match confidence to evaluate a pair (default: 0.5)")
    parser.add_argument("--min-absolute-margin", type=float, default=200.0,
                        help="Minimum absolute profit in INR per unit (default: 200)")
    parser.add_argument("--min-margin-pct", type=float, default=35.0,
                        help="Minimum gross margin percentage (default: 35)")
    parser.add_argument("--min-ticket-price", type=float, default=300.0,
                        help="Minimum Amazon price in INR; lower-ticket items are discarded (default: 300)")
    args = parser.parse_args()
    run_matching_pipeline(
        min_confidence=args.min_confidence,
        min_absolute_margin=args.min_absolute_margin,
        min_margin_pct=args.min_margin_pct,
        min_ticket_price=args.min_ticket_price,
    )