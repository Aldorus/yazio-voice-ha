import time

import pytest
import responses

from yazio_client.auth import YazioAuth
from yazio_client.const import TOKEN_ENDPOINT
from yazio_client.exceptions import YazioAuthError

TOKEN_RESPONSE = {
    "access_token": "fake-access",
    "refresh_token": "fake-refresh",
    "expires_in": 172800,
    "token_type": "bearer",
}


@responses.activate
def test_login_success_stores_tokens():
    responses.add(responses.POST, TOKEN_ENDPOINT, json=TOKEN_RESPONSE, status=200)

    auth = YazioAuth()
    tokens = auth.login("user@example.com", "hunter2")

    assert tokens.access_token == "fake-access"
    assert tokens.refresh_token == "fake-refresh"
    assert not tokens.is_expired

    sent_body = responses.calls[0].request.body
    assert "password=hunter2" in sent_body
    assert "grant_type=password" in sent_body


def test_login_requires_credentials():
    auth = YazioAuth()
    with pytest.raises(YazioAuthError):
        auth.login("", "")


@responses.activate
def test_login_failure_raises():
    responses.add(responses.POST, TOKEN_ENDPOINT, json={"error": "invalid_grant"}, status=400)

    auth = YazioAuth()
    with pytest.raises(YazioAuthError):
        auth.login("user@example.com", "wrong-password")


@responses.activate
def test_ensure_valid_token_refreshes_when_expired():
    responses.add(responses.POST, TOKEN_ENDPOINT, json=TOKEN_RESPONSE, status=200)
    auth = YazioAuth()
    auth.login("user@example.com", "hunter2")

    # Force l'expiration du token courant.
    auth._tokens.expires_at = time.time() - 1

    refreshed_response = {**TOKEN_RESPONSE, "access_token": "fake-access-2"}
    responses.replace(responses.POST, TOKEN_ENDPOINT, json=refreshed_response, status=200)

    tokens = auth.ensure_valid_token()

    assert tokens.access_token == "fake-access-2"
    refresh_call_body = responses.calls[-1].request.body
    assert "grant_type=refresh_token" in refresh_call_body
    assert "refresh_token=fake-refresh" in refresh_call_body


def test_ensure_valid_token_without_login_raises():
    auth = YazioAuth()
    with pytest.raises(YazioAuthError):
        auth.ensure_valid_token()


@responses.activate
def test_on_token_update_callback_called():
    responses.add(responses.POST, TOKEN_ENDPOINT, json=TOKEN_RESPONSE, status=200)

    seen = []
    auth = YazioAuth(on_token_update=seen.append)
    auth.login("user@example.com", "hunter2")

    assert len(seen) == 1
    assert seen[0].access_token == "fake-access"


@responses.activate
def test_load_tokens_skips_login():
    from yazio_client.auth import TokenSet

    auth = YazioAuth()
    auth.load_tokens(
        TokenSet(
            access_token="persisted-access",
            refresh_token="persisted-refresh",
            token_type="bearer",
            expires_at=time.time() + 1000,
        )
    )

    tokens = auth.ensure_valid_token()
    assert tokens.access_token == "persisted-access"
    assert len(responses.calls) == 0
