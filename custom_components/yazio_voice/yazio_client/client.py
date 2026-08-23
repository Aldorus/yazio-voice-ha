from __future__ import annotations

import logging
import uuid
from datetime import date as date_type
from typing import Optional

import requests

from .auth import YazioAuth
from .const import BASE_URL, REQUEST_TIMEOUT, USER_AGENT
from .exceptions import YazioError

_LOGGER = logging.getLogger(__name__)

DAYTIMES = ("breakfast", "lunch", "dinner", "snack")


def _as_date_str(value) -> str:
    if isinstance(value, date_type):
        return value.isoformat()
    return str(value)


class YazioClient:
    """Client Yazio de haut niveau : recherche produit + journal (intake).

    Toute la logique réseau spécifique à Yazio (endpoints, formats) est
    isolée ici, derrière cette seule classe, pour pouvoir patcher vite en
    cas de changement de l'API non officielle.
    """

    def __init__(self, auth: YazioAuth, session: Optional[requests.Session] = None) -> None:
        self._auth = auth
        self._session = session or requests.Session()

    def login(self, username: str, password: str) -> None:
        self._auth.login(username, password)

    def search_products(
        self,
        query: str,
        sex: str = "male",
        countries: Optional[list[str]] = None,
        locales: Optional[list[str]] = None,
    ) -> list[dict]:
        params = {
            "query": query,
            "sex": sex,
            "countries": ",".join(countries or ["FR", "US"]),
            "locales": ",".join(locales or ["fr_FR", "en_US"]),
        }
        return self._get("/products/search", params=params)

    def get_product(self, product_id: str) -> Optional[dict]:
        return self._get(f"/products/{product_id}")

    def get_consumed_items(self, date) -> dict:
        return self._get("/user/consumed-items", params={"date": _as_date_str(date)})

    def add_consumed_item(
        self,
        product_id: str,
        date,
        daytime: str,
        amount: float,
        serving: Optional[str] = None,
        serving_quantity: Optional[float] = None,
    ) -> str:
        """Log un aliment dans le journal Yazio.

        `amount` est toujours en unité de base du produit (g ou ml).
        `serving`/`serving_quantity` sont optionnels et n'existent que pour
        affichage cohérent côté app Yazio (ex: "2 portions").
        """
        if daytime not in DAYTIMES:
            raise YazioError(f"daytime invalide: {daytime!r} (attendu: {DAYTIMES})")

        item_id = str(uuid.uuid4())
        body = {
            "recipe_portions": [],
            "simple_products": [],
            "products": [
                {
                    "id": item_id,
                    "product_id": product_id,
                    "date": _as_date_str(date),
                    "daytime": daytime,
                    "amount": amount,
                    "serving": serving,
                    "serving_quantity": serving_quantity,
                }
            ],
        }
        self._post("/user/consumed-items", json_body=body)
        return item_id

    def remove_consumed_item(self, item_id: str) -> None:
        self._request("DELETE", "/user/consumed-items", json_body=[item_id])

    def _get(self, path: str, params: Optional[dict] = None):
        return self._request("GET", path, params=params)

    def _post(self, path: str, json_body):
        return self._request("POST", path, json_body=json_body)

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_body=None,
    ):
        token = self._auth.ensure_valid_token()
        headers = {
            "Authorization": f"{token.token_type.capitalize()} {token.access_token}",
            "User-Agent": USER_AGENT,
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            response = self._session.request(
                method,
                f"{BASE_URL}{path}",
                params=params,
                json=json_body,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise YazioError(f"Requête Yazio impossible ({method} {path}): {exc}") from exc

        if response.status_code >= 400:
            _LOGGER.warning("Yazio %s %s -> %s", method, path, response.status_code)
            raise YazioError(f"Yazio a refusé la requête ({method} {path}, status={response.status_code})")

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise YazioError(f"Réponse Yazio illisible ({method} {path})") from exc
