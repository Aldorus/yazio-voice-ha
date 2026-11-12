import time

import pytest
import responses

from yazio_client.auth import TokenSet, YazioAuth
from yazio_client.client import YazioClient
from yazio_client.const import BASE_URL
from yazio_client.exceptions import YazioError

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
def test_search_products_sends_query_and_auth_header():
    responses.add(
        responses.GET,
        f"{BASE_URL}/products/search",
        json=[{"product_id": PRODUCT_ID, "name": "Pomme", "score": 0.9}],
        status=200,
    )

    client = _authed_client()
    results = client.search_products("pomme")

    assert results[0]["name"] == "Pomme"
    sent = responses.calls[0].request
    assert sent.headers["Authorization"] == "Bearer fake-access"
    assert "query=pomme" in sent.url


@responses.activate
def test_add_consumed_item_posts_expected_body():
    responses.add(responses.POST, f"{BASE_URL}/user/consumed-items", json={}, status=200)

    client = _authed_client()
    item_id = client.add_consumed_item(
        product_id=PRODUCT_ID,
        date="2026-08-23",
        daytime="breakfast",
        amount=150,
    )

    assert item_id  # uuid generated client-side

    import json

    body = json.loads(responses.calls[0].request.body)
    assert body["products"][0]["product_id"] == PRODUCT_ID
    assert body["products"][0]["daytime"] == "breakfast"
    assert body["products"][0]["amount"] == 150
    assert body["products"][0]["id"] == item_id
    assert body["recipe_portions"] == []
    assert body["simple_products"] == []


def test_add_consumed_item_rejects_invalid_daytime():
    client = _authed_client()
    with pytest.raises(YazioError):
        client.add_consumed_item(
            product_id=PRODUCT_ID,
            date="2026-08-23",
            daytime="brunch",
            amount=100,
        )


@responses.activate
def test_get_product():
    responses.add(
        responses.GET,
        f"{BASE_URL}/products/{PRODUCT_ID}",
        json={"id": PRODUCT_ID, "name": "Pomme", "base_unit": "g"},
        status=200,
    )

    client = _authed_client()
    product = client.get_product(PRODUCT_ID)

    assert product["name"] == "Pomme"


@responses.activate
def test_remove_consumed_item_sends_delete_with_id_list():
    responses.add(responses.DELETE, f"{BASE_URL}/user/consumed-items", json={}, status=200)

    client = _authed_client()
    client.remove_consumed_item("some-item-id")

    import json

    body = json.loads(responses.calls[0].request.body)
    assert body == ["some-item-id"]


@responses.activate
def test_request_error_raises_yazio_error():
    responses.add(
        responses.GET,
        f"{BASE_URL}/products/search",
        json={"error": "server error"},
        status=500,
    )

    client = _authed_client()
    with pytest.raises(YazioError):
        client.search_products("pomme")
