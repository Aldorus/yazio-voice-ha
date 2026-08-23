from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN
from .yazio_client import YazioAuth, YazioError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
    }
)


class YazioVoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            auth = YazioAuth()
            try:
                tokens = await self.hass.async_add_executor_job(
                    auth.login, user_input["email"], user_input["password"]
                )
            except YazioError:
                _LOGGER.warning("Login Yazio refusé lors de la configuration")
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(user_input["email"])
                self._abort_if_unique_id_configured()
                # Seuls les tokens sont conservés — jamais le mot de passe.
                return self.async_create_entry(
                    title=user_input["email"],
                    data={"tokens": tokens.as_dict()},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
