import time

import responses

from yazio_client.auth import TokenSet, YazioAuth
from yazio_client.client import YazioClient
from yazio_client.const import BASE_URL
from yazio_client.resolver import compute_amount, search_food

PRODUCT_ID = "5b1b3b1e-0000-4000-8000-000000000001"


def _authed_client() -> YazioClient:
    auth = YazioAuth()
    auth.load_tokens(
        TokenSet(
            access_token="fake-access",
            refresh_token="fake-refresh",
            token_type="bearer",
            expires_at=time.time() + 1000,
        )
    )
    return YazioClient(auth)


@responses.activate
def test_search_food_ranks_by_score():
    responses.add(
        responses.GET,
        f"{BASE_URL}/products/search",
        json=[
            {"product_id": "low", "name": "Pomme chips", "score": 0.2, "base_unit": "g", "serving": "g", "serving_quantity": 1, "amount": 100},
            {"product_id": "high", "name": "Pomme", "score": 0.95, "base_unit": "g", "serving": "g", "serving_quantity": 1, "amount": 100},
        ],
        status=200,
    )

    client = _authed_client()
    resolution = search_food(client, "pomme")

    assert resolution.best.product_id == "high"
    assert resolution.matches[1].product_id == "low"


@responses.activate
def test_search_food_no_results():
    responses.add(responses.GET, f"{BASE_URL}/products/search", json=[], status=200)

    client = _authed_client()
    resolution = search_food(client, "inexistant")

    assert resolution.best is None


def _match(**overrides):
    from yazio_client.resolver import ProductMatch

    base = dict(
        product_id=PRODUCT_ID,
        name="Pomme",
        producer="",
        score=0.9,
        base_unit="g",
        default_serving="g",
        default_serving_quantity=1,
        default_amount=100,
    )
    base.update(overrides)
    return ProductMatch(**base)


def test_compute_amount_direct_base_unit():
    client = _authed_client()
    match = _match()

    amount, serving, serving_qty = compute_amount(client, match, 150, "grammes")

    assert amount == 150
    assert serving is None
    assert serving_qty is None


def test_compute_amount_default_serving_alias():
    client = _authed_client()
    match = _match(default_serving="piece", default_amount=182)

    amount, serving, serving_qty = compute_amount(client, match, 2, "piece")

    assert amount == 364
    assert serving == "piece"
    assert serving_qty == 2


@responses.activate
def test_compute_amount_looks_up_product_servings():
    responses.add(
        responses.GET,
        f"{BASE_URL}/products/{PRODUCT_ID}",
        json={
            "id": PRODUCT_ID,
            "base_unit": "g",
            "servings": [
                {"serving": "gram", "amount": 1},
                {"serving": "cup", "amount": 125},
            ],
        },
        status=200,
    )

    client = _authed_client()
    match = _match(default_serving="gram", default_amount=1)

    amount, serving, serving_qty = compute_amount(client, match, 1, "cup")

    assert amount == 125
    assert serving == "cup"
    assert serving_qty == 1


@responses.activate
def test_compute_amount_unknown_unit_falls_back_to_raw_quantity():
    responses.add(
        responses.GET,
        f"{BASE_URL}/products/{PRODUCT_ID}",
        json={"id": PRODUCT_ID, "base_unit": "g", "servings": []},
        status=200,
    )

    client = _authed_client()
    match = _match()

    amount, serving, serving_qty = compute_amount(client, match, 3, "bol")

    assert amount == 3
    assert serving is None
    assert serving_qty is None
