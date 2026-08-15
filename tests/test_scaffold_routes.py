"""
Tests for the SCAFFOLD — the code that oauth-init drops into a user's project.

This is the code that actually ships, so it's the code that most needs tests.
The scaffold imports `oauth_config` as a top-level module (that's how it lands in
a user's project), so we stub that module before importing the routes.

Run with: pytest tests/ -v
"""

from __future__ import annotations

import importlib
import sys
import types

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SCAFFOLD_DIR = "oauth_for_dummies/scaffold"

FAKE_PROVIDER = {
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
    "authorize_url": "https://example.test/authorize",
    "token_url": "https://example.test/token",
    "userinfo_url": "https://example.test/userinfo",
    "scopes": ["read:user"],
    "name": "Example",
}


@pytest.fixture
def routes(monkeypatch):
    """Import the scaffold's oauth_routes with a stubbed oauth_config."""
    fake_config = types.ModuleType("oauth_config")
    fake_config.OAUTH_PROVIDERS = {"example": dict(FAKE_PROVIDER)}
    fake_config.OAUTH_BASE_URL = "http://localhost:8000"
    monkeypatch.setitem(sys.modules, "oauth_config", fake_config)

    # Load oauth_routes.py from the scaffold directory by path
    spec = importlib.util.spec_from_file_location(
        "scaffold_oauth_routes", f"{SCAFFOLD_DIR}/oauth_routes.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "scaffold_oauth_routes", module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client(routes):
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# Login CSRF — the important one
# ---------------------------------------------------------------------------

class TestStateIsBoundToBrowser:
    """
    A state token must only be redeemable by the browser that started the flow.

    Without this, an attacker can start a login, authorize as themselves, capture
    code+state, and feed the callback URL to a victim. The victim's browser then
    gets a session for the ATTACKER's account. That's login CSRF (RFC 6749 §10.12).
    """

    def test_login_sets_state_cookie(self, client, routes):
        resp = client.get("/auth/example/login")
        assert resp.status_code == 307
        assert routes.STATE_COOKIE in resp.cookies

        # The cookie value must be the same state sent to the provider
        assert f"state={resp.cookies[routes.STATE_COOKIE]}" in resp.headers["location"]

    def test_state_from_another_browser_is_rejected(self, client, routes):
        """THE regression test: attacker's state, victim's browser."""
        # Attacker starts a flow and captures a genuine, server-issued state
        attacker = client.get("/auth/example/login")
        attacker_state = attacker.cookies[routes.STATE_COOKIE]

        # Victim's browser has no matching cookie, but the state IS valid
        # server-side — this is exactly what the old code accepted.
        victim = TestClient(client.app, follow_redirects=False)
        resp = victim.get(
            f"/auth/example/callback?code=stolen-code&state={attacker_state}"
        )

        assert resp.status_code == 400
        assert "browser" in resp.json()["detail"].lower()

    def test_forged_state_matching_cookie_is_still_rejected(self, client):
        """
        Cookie match alone isn't enough either — the state must be one we issued.
        An attacker who can set cookies must not be able to mint their own state.
        """
        client.cookies.set("oauth_state", "forged-state-value")
        resp = client.get("/auth/example/callback?code=abc&state=forged-state-value")

        assert resp.status_code == 400
        assert "invalid state" in resp.json()["detail"].lower()

    def test_missing_state_is_rejected(self, client):
        resp = client.get("/auth/example/callback?code=abc")
        assert resp.status_code == 400

    def test_state_is_single_use(self, client, routes, monkeypatch):
        """A state must not be redeemable twice, even by the right browser."""
        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]

        # Consume it once (token exchange fails, but the state is spent)
        _stub_token_error(monkeypatch, routes)
        client.get(f"/auth/example/callback?code=abc&state={state}")

        resp = client.get(f"/auth/example/callback?code=abc&state={state}")
        assert resp.status_code == 400
        assert "invalid state" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PKCE
# ---------------------------------------------------------------------------

class TestPKCE:
    def test_no_pkce_params_by_default(self, client):
        resp = client.get("/auth/example/login")
        assert "code_challenge" not in resp.headers["location"]

    def test_pkce_adds_s256_challenge(self, client, routes):
        routes.PKCE_PROVIDERS.add("example")
        resp = client.get("/auth/example/login")

        assert "code_challenge=" in resp.headers["location"]
        assert "code_challenge_method=S256" in resp.headers["location"]

    def test_confidential_client_sends_secret_AND_verifier(self, client, routes, monkeypatch):
        """
        PKCE supplements client_secret, it does not replace it.

        Web apps are confidential clients. GitHub, Google, Discord, Microsoft and
        LinkedIn all reject a token request with no secret, so dropping it when
        PKCE is on breaks every one of them.
        """
        routes.PKCE_PROVIDERS.add("example")
        sent = _capture_token_request(monkeypatch, routes)

        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]
        client.get(f"/auth/example/callback?code=abc&state={state}")

        assert sent["body"]["client_secret"] == "test-client-secret"
        assert "code_verifier" in sent["body"]

    def test_public_client_omits_secret(self, client, routes, monkeypatch):
        routes.PKCE_PROVIDERS.add("example")
        routes.PUBLIC_CLIENTS.add("example")
        sent = _capture_token_request(monkeypatch, routes)

        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]
        client.get(f"/auth/example/callback?code=abc&state={state}")

        assert "client_secret" not in sent["body"]
        assert "code_verifier" in sent["body"]

    def test_challenge_is_sha256_of_verifier(self, routes):
        verifier = routes._generate_code_verifier()
        challenge = routes._generate_code_challenge(verifier)

        import base64, hashlib
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        assert challenge == expected
        assert "=" not in challenge  # base64url, unpadded


# ---------------------------------------------------------------------------
# Token error handling
# ---------------------------------------------------------------------------

class TestTokenErrors:
    def test_github_style_200_with_error_body(self, client, routes, monkeypatch):
        """
        GitHub returns HTTP 200 with an error body. raise_for_status() sees a
        healthy response, and the old code then died on token_json["access_token"]
        with a 500 + traceback.
        """
        _stub_token_error(monkeypatch, routes, error="bad_verification_code")

        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]
        resp = client.get(f"/auth/example/callback?code=expired&state={state}")

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "bad_verification_code" in detail
        assert "single-use" in detail  # the friendly explanation

    def test_error_description_is_surfaced(self, client, routes, monkeypatch):
        _stub_token_error(
            monkeypatch, routes,
            error="redirect_uri_mismatch",
            description="The redirect_uri MUST match the registered callback URL.",
        )

        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]
        resp = client.get(f"/auth/example/callback?code=abc&state={state}")

        assert "MUST match the registered callback URL" in resp.json()["detail"]

    def test_missing_access_token_is_not_a_500(self, client, routes, monkeypatch):
        _stub_token_response(monkeypatch, routes, {"token_type": "bearer"})

        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]
        resp = client.get(f"/auth/example/callback?code=abc&state={state}")

        assert resp.status_code == 502
        assert "access_token" in resp.json()["detail"]

    def test_non_json_response_is_not_a_500(self, client, routes, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="<html>gateway error</html>")

        _install_transport(monkeypatch, routes, handler)

        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]
        resp = client.get(f"/auth/example/callback?code=abc&state={state}")

        assert resp.status_code == 502
        assert "non-JSON" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _install_transport(monkeypatch, routes, handler):
    """Route all httpx calls made by the scaffold through a mock transport."""
    original = httpx.AsyncClient

    class MockClient(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(routes.httpx, "AsyncClient", MockClient)


def _stub_token_response(monkeypatch, routes, payload: dict, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    _install_transport(monkeypatch, routes, handler)


def _stub_token_error(monkeypatch, routes, error: str = "invalid_grant", description: str = ""):
    payload = {"error": error}
    if description:
        payload["error_description"] = description
    _stub_token_response(monkeypatch, routes, payload)


def _capture_token_request(monkeypatch, routes) -> dict:
    """Capture the token request body, then return a valid token + user."""
    from urllib.parse import parse_qs

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            body = parse_qs(request.content.decode())
            captured["body"] = {k: v[0] for k, v in body.items()}
            return httpx.Response(200, json={"access_token": "tok", "token_type": "bearer"})
        return httpx.Response(200, json={"id": 1, "name": "Test User"})

    _install_transport(monkeypatch, routes, handler)
    return captured
