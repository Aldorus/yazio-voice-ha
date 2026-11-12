from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

import requests

from .const import CLIENT_ID, CLIENT_SECRET, REQUEST_TIMEOUT, TOKEN_ENDPOINT, USER_AGENT
from .exceptions import YazioAuthError

_LOGGER = logging.getLogger(__name__)

# Margin before expiry at which a preventive refresh is triggered.
_EXPIRY_MARGIN_SECONDS = 60


@dataclass
class TokenSet:
    """Yazio token pair. Never contains the password."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_at: float  # epoch seconds

    @property
    def is_expired(self) -> bool:
        return time.time() >= (self.expires_at - _EXPIRY_MARGIN_SECONDS)

    def as_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenSet":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data["token_type"],
            expires_at=data["expires_at"],
        )

    @classmethod
    def _from_token_response(cls, payload: dict) -> "TokenSet":
        return cls(
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            token_type=payload.get("token_type", "bearer"),
            expires_at=time.time() + payload["expires_in"],
        )


class YazioAuth:
    """Handles the login/password -> tokens exchange and token refresh.

    The password is only used for the first login and is never kept by
    this class. Only the tokens are held in memory; `on_token_update`
    lets the caller (e.g. the Home Assistant integration) persist them
    (config entry storage, etc).
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        on_token_update: Optional[Callable[[TokenSet], None]] = None,
    ) -> None:
        self._session = session or requests.Session()
        self._on_token_update = on_token_update
        self._tokens: Optional[TokenSet] = None

    @property
    def tokens(self) -> Optional[TokenSet]:
        return self._tokens

    def load_tokens(self, tokens: TokenSet) -> None:
        """Re-inject previously persisted tokens (no new login)."""
        self._tokens = tokens

    def login(self, username: str, password: str) -> TokenSet:
        if not username or not password:
            raise YazioAuthError("Missing Yazio credentials")

        response = self._post_token(
            {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": username,
                "password": password,
            }
        )
        self._tokens = TokenSet._from_token_response(response)
        self._notify_update()
        return self._tokens

    def ensure_valid_token(self) -> TokenSet:
        """Return a valid access token, refreshing it if needed."""
        if self._tokens is None:
            raise YazioAuthError("No token loaded, call login() first")
        if self._tokens.is_expired:
            self._refresh()
        return self._tokens

    def _refresh(self) -> TokenSet:
        assert self._tokens is not None
        response = self._post_token(
            {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self._tokens.refresh_token,
            }
        )
        self._tokens = TokenSet._from_token_response(response)
        self._notify_update()
        return self._tokens

    def _post_token(self, form_data: dict) -> dict:
        try:
            response = self._session.post(
                TOKEN_ENDPOINT,
                data=form_data,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise YazioAuthError(f"Request to Yazio failed: {exc}") from exc

        if response.status_code != 200:
            _LOGGER.warning("Yazio auth rejected (status=%s)", response.status_code)
            raise YazioAuthError(f"Yazio auth rejected (status={response.status_code})")

        try:
            payload = response.json()
        except ValueError as exc:
            raise YazioAuthError("Unreadable Yazio response (not JSON)") from exc

        for field in ("access_token", "refresh_token", "expires_in"):
            if field not in payload:
                raise YazioAuthError(f"Incomplete Yazio response, missing field: {field}")

        return payload

    def _notify_update(self) -> None:
        _LOGGER.debug("Yazio tokens updated")
        if self._on_token_update and self._tokens is not None:
            self._on_token_update(self._tokens)
