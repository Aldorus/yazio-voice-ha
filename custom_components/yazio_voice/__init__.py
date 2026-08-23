from __future__ import annotations

import datetime as dt
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse

from .const import DOMAIN
from .yazio_client import TokenSet, YazioAuth, YazioClient, YazioError
from .yazio_client.client import DAYTIMES
from .yazio_client.resolver import compute_amount, search_food

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    def _persist_tokens(tokens: TokenSet) -> None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "tokens": tokens.as_dict()}
        )

    auth = YazioAuth(on_token_update=_persist_tokens)
    auth.load_tokens(TokenSet.from_dict(entry.data["tokens"]))
    client = YazioClient(auth)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    async def handle_search_food(call: ServiceCall) -> ServiceResponse:
        food = call.data["food"]
        quantity = float(call.data["quantity"])
        unit = call.data["unit"]

        def _do() -> ServiceResponse:
            resolution = search_food(client, food)
            if resolution.best is None:
                return {"found": False}
            amount, serving, serving_quantity = compute_amount(
                client, resolution.best, quantity, unit
            )
            return {
                "found": True,
                "product_id": resolution.best.product_id,
                "name": resolution.best.name,
                "producer": resolution.best.producer,
                "amount": amount,
                "serving": serving,
                "serving_quantity": serving_quantity,
                "alternatives": [
                    {"product_id": m.product_id, "name": m.name}
                    for m in resolution.matches[1:4]
                ],
            }

        try:
            return await hass.async_add_executor_job(_do)
        except YazioError as exc:
            _LOGGER.warning("Recherche Yazio échouée pour '%s': %s", food, exc)
            return {"found": False, "error": str(exc)}

    async def handle_log_food(call: ServiceCall) -> ServiceResponse:
        meal = call.data["meal"]
        if meal not in DAYTIMES:
            return {"logged": False, "error": f"meal invalide: {meal!r}"}

        product_id = call.data["product_id"]
        amount = float(call.data["amount"])
        serving = call.data.get("serving") or None
        serving_quantity = call.data.get("serving_quantity") or None

        def _do() -> str:
            return client.add_consumed_item(
                product_id=product_id,
                date=dt.date.today(),
                daytime=meal,
                amount=amount,
                serving=serving,
                serving_quantity=serving_quantity,
            )

        try:
            item_id = await hass.async_add_executor_job(_do)
        except YazioError as exc:
            _LOGGER.warning("Écriture Yazio échouée: %s", exc)
            return {"logged": False, "error": str(exc)}
        return {"logged": True, "item_id": item_id}

    hass.services.async_register(
        DOMAIN, "search_food", handle_search_food, supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register(
        DOMAIN, "log_food", handle_log_food, supports_response=SupportsResponse.ONLY
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    hass.services.async_remove(DOMAIN, "search_food")
    hass.services.async_remove(DOMAIN, "log_food")
    return True
