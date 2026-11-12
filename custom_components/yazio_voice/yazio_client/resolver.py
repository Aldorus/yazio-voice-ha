from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from .client import YazioClient
from .units import is_base_unit_alias, normalize

_LOGGER = logging.getLogger(__name__)


@dataclass
class ProductMatch:
    product_id: str
    name: str
    producer: str
    score: float
    base_unit: str
    default_serving: str
    default_serving_quantity: float
    default_amount: float


@dataclass
class FoodResolution:
    query: str
    matches: list[ProductMatch] = field(default_factory=list)

    @property
    def best(self) -> Optional[ProductMatch]:
        return self.matches[0] if self.matches else None


def _to_match(raw: dict) -> ProductMatch:
    return ProductMatch(
        product_id=raw["product_id"],
        name=raw.get("name", ""),
        producer=raw.get("producer", ""),
        score=raw.get("score", 0.0),
        base_unit=raw.get("base_unit", "g"),
        default_serving=raw.get("serving", "g"),
        default_serving_quantity=raw.get("serving_quantity", 1),
        default_amount=raw.get("amount", 100),
    )


def search_food(client: YazioClient, food: str, max_results: int = 5) -> FoodResolution:
    """Search-first: queries the Yazio DB, logs nothing."""
    raw_results = client.search_products(food) or []
    ranked = sorted(raw_results, key=lambda r: r.get("score", 0.0), reverse=True)
    matches = [_to_match(r) for r in ranked[:max_results]]
    return FoodResolution(query=food, matches=matches)


def compute_amount(
    client: YazioClient, match: ProductMatch, quantity: float, unit: str
) -> tuple[float, Optional[str], Optional[float]]:
    """Convert the dictated (quantity, unit) into (amount, serving,
    serving_quantity) in the format expected by `add_consumed_item`.

    `amount` is always in the product's base unit (g/ml).
    """
    if is_base_unit_alias(unit, match.base_unit):
        return quantity, None, None

    if is_base_unit_alias(unit, match.default_serving):
        return quantity * match.default_amount, match.default_serving, quantity

    product = client.get_product(match.product_id) or {}
    for serving in product.get("servings", []):
        if normalize(serving["serving"]) == normalize(unit):
            return quantity * serving["amount"], serving["serving"], quantity

    _LOGGER.warning(
        "Unit '%s' not recognised for '%s' (base_unit=%s) — quantity used as-is",
        unit,
        match.name,
        match.base_unit,
    )
    return quantity, None, None
