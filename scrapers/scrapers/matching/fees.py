"""Marketplace fee models for net-margin math (stdlib only).

Only marketplaces with a researched, documented fee schedule are registered.
An unregistered marketplace yields ``None`` (``INSUFFICIENT_DATA``) from every
model method - fees are never fabricated for unknown marketplaces.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

_FEE = float
FEE_TIER = Tuple[_FEE, _FEE]

_UNBOUNDED = float("inf")


@dataclass(frozen=True)
class MarketplaceFeeModel:
    name: str
    closing_fee_tiers: Tuple[FEE_TIER, ...] = ()
    shipping_fee_tiers: Tuple[FEE_TIER, ...] = ()
    referral_rate: Optional[float] = None
    gst_rate: Optional[float] = 0.18

    def _tier(self, tiers: Tuple[FEE_TIER, ...], value: float) -> Optional[float]:
        if not tiers:
            return None
        fee = tiers[0][1]
        for max_value, fee_amount in tiers:
            if value <= max_value:
                return fee_amount
            fee = fee_amount
        return fee

    def referral_fee(self, price: float) -> Optional[float]:
        if self.referral_rate is None:
            return None
        return price * self.referral_rate

    def closing_fee(self, price: float) -> Optional[float]:
        return self._tier(self.closing_fee_tiers, price)

    def shipping_fee(self, weight_g: int) -> Optional[float]:
        return self._tier(self.shipping_fee_tiers, float(weight_g))

    def fee_total(self, price: float, weight_g: int) -> Optional[float]:
        referral = self.referral_fee(price)
        closing = self.closing_fee(price)
        shipping = self.shipping_fee(weight_g)
        if referral is None or closing is None or shipping is None:
            return None
        gst_on_fees = (closing + shipping) * self.gst_rate if self.gst_rate is not None else 0.0
        return referral + closing + shipping + gst_on_fees


FEE_MODELS = {
    "amazon": MarketplaceFeeModel(
        name="amazon",
        referral_rate=0.15,
        closing_fee_tiers=((250, 5.0), (_UNBOUNDED, 10.0)),
        shipping_fee_tiers=((200, 16.0), (500, 22.0), (_UNBOUNDED, 35.0)),
        gst_rate=0.18,
    ),
}


def get_fee_model(name: str) -> Optional[MarketplaceFeeModel]:
    return FEE_MODELS.get(name)
