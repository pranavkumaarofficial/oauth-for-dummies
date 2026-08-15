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
import time
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


def _load_scaffold_routes(monkeypatch):
    """
    Import the scaffold's oauth_routes.py with a stubbed oauth_config.

    Loaded by path and re-executed per test, because the scaffold is written to
    be dropped into a user's project as a top-level module, not imported as part
    of this package. Re-executing also gives each test fresh module state.
    """
    fake_config = types.ModuleType("oauth_config")
    fake_config.OAUTH_PROVIDERS = {"example": dict(FAKE_PROVIDER)}
    fake_config.OAUTH_BASE_URL = "http://localhost:8000"
    monkeypatch.setitem(sys.modules, "oauth_config", fake_config)

    spec = importlib.util.spec_from_file_location(
        "scaffold_oauth_routes", f"{SCAFFOLD_DIR}/oauth_routes.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "scaffold_oauth_routes", module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def routes(monkeypatch):
    # Clear COOKIE_SECURE so the suite behaves the same on every machine. The
    # test client speaks http, and browsers (correctly) do not return Secure
    # cookies over http — so leaving it set would break every cookie-dependent
    # test here. The tests that care about the flag set it explicitly.
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    return _load_scaffold_routes(monkeypatch)


@pytest.fixture
def client(routes):
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def example_app(routes, monkeypatch):
    """The generated oauth_example_app.py, wired to the loaded routes module."""
    monkeypatch.setitem(sys.modules, "oauth_routes", routes)

    spec = importlib.util.spec_from_file_location(
        "scaffold_example_app", f"{SCAFFOLD_DIR}/oauth_example_app.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


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
# End to end — a full successful login through the generated app
# ---------------------------------------------------------------------------

class TestFullLoginFlow:
    """
    Drive the whole scaffold the way a user's browser would: login redirect,
    callback, session cookie, profile page, logout. Every other test here checks
    a failure path, so this is the one proving the happy path still works.
    """

    def test_login_redirects_to_provider_with_correct_params(self, client):
        resp = client.get("/auth/example/login")
        location = resp.headers["location"]

        assert location.startswith("https://example.test/authorize?")
        assert "client_id=test-client-id" in location
        assert "response_type=code" in location
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fexample%2Fcallback" in location

    def test_successful_login_creates_session_and_renders_profile(self, example_app, routes, monkeypatch):
        _stub_full_flow(monkeypatch, routes, user={"id": 7, "name": "Ada Lovelace"})
        browser = TestClient(example_app, follow_redirects=False)

        # 1. start the flow
        login = browser.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]

        # 2. the provider redirects back
        callback = browser.get(f"/auth/example/callback?code=good-code&state={state}")
        assert callback.status_code == 303
        assert callback.headers["location"] == "/profile"
        assert "session_id" in callback.cookies

        # 3. the session works
        profile = browser.get("/profile")
        assert profile.status_code == 200
        assert "Ada Lovelace" in profile.text

        # 4. logout clears it
        browser.get("/auth/logout")
        assert browser.get("/profile").status_code == 401

    def test_hostile_display_name_is_escaped_not_executed(self, example_app, routes, monkeypatch):
        """
        A provider display name is attacker-controlled. It must render as text.
        """
        payload = '<img src=x onerror="alert(1)">'
        _stub_full_flow(monkeypatch, routes, user={"id": 1, "name": payload})
        browser = TestClient(example_app, follow_redirects=False)

        login = browser.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]
        browser.get(f"/auth/example/callback?code=good-code&state={state}")

        profile = browser.get("/profile")

        assert "<img src=x" not in profile.text      # no live tag
        assert "&lt;img src=x" in profile.text        # rendered as text
        assert 'onerror="alert(1)"' not in profile.text

    def test_profile_requires_a_session(self, example_app):
        assert TestClient(example_app).get("/profile").status_code == 401


# ---------------------------------------------------------------------------
# Expiry — enforced server-side, not via cookie max_age
# ---------------------------------------------------------------------------

class TestExpiry:
    def test_expired_state_cannot_be_redeemed(self, client, routes):
        login = client.get("/auth/example/login")
        state = login.cookies[routes.STATE_COOKIE]

        # Age the pending state past its TTL
        provider, born = routes._pending_states[state]
        routes._pending_states[state] = (provider, born - routes.STATE_TTL - 1)

        resp = client.get(f"/auth/example/callback?code=abc&state={state}")

        assert resp.status_code == 400
        assert "invalid state" in resp.json()["detail"].lower()

    def test_sweep_evicts_expired_states(self, routes):
        now = 1_000_000.0
        routes._pending_states.clear()
        routes._pending_states["fresh"] = ("example", now)
        routes._pending_states["stale"] = ("example", now - routes.STATE_TTL - 1)
        routes._code_verifiers["stale"] = "verifier-for-stale"

        routes._sweep(now=now)

        assert "fresh" in routes._pending_states
        assert "stale" not in routes._pending_states
        # the PKCE verifier must not be left behind
        assert "stale" not in routes._code_verifiers

    def test_unauthenticated_logins_do_not_grow_state_table(self, client, routes):
        """
        /login is unauthenticated. Without eviction it's an unbounded-memory DoS.
        """
        routes._pending_states.clear()
        for _ in range(20):
            client.get("/auth/example/login")
        assert len(routes._pending_states) == 20

        # Age everything, then one more login should sweep the lot
        aged = {s: (p, born - routes.STATE_TTL - 1) for s, (p, born) in routes._pending_states.items()}
        routes._pending_states.update(aged)
        client.get("/auth/example/login")

        assert len(routes._pending_states) == 1

    def test_expired_session_is_not_returned(self, routes):
        """A leaked cookie must stop working, whatever max_age the browser saw."""
        request = _fake_request({"session_id": "sid"})

        routes._sessions["sid"] = ({"name": "Alice"}, time.time())
        assert routes.get_session(request)["name"] == "Alice"

        routes._sessions["sid"] = ({"name": "Alice"}, time.time() - routes.SESSION_TTL - 1)
        assert routes.get_session(request) is None
        assert "sid" not in routes._sessions  # and it's evicted


# ---------------------------------------------------------------------------
# Cookie flags
# ---------------------------------------------------------------------------

class TestCookieFlags:
    def test_state_cookie_is_httponly_and_lax(self, client, routes):
        resp = client.get("/auth/example/login")
        header = resp.headers["set-cookie"]

        assert "HttpOnly" in header
        assert "lax" in header.lower()

    def test_secure_flag_off_by_default_for_localhost(self, monkeypatch):
        """Must default off, or http://localhost dev silently loses its cookies."""
        monkeypatch.delenv("COOKIE_SECURE", raising=False)
        module = _load_scaffold_routes(monkeypatch)

        app = FastAPI()
        app.include_router(module.router)
        resp = TestClient(app, follow_redirects=False).get("/auth/example/login")

        assert module.COOKIE_SECURE is False
        assert "Secure" not in resp.headers["set-cookie"]

    def test_secure_flag_set_when_env_var_enabled(self, monkeypatch):
        """COOKIE_SECURE=true must actually reach the Set-Cookie header."""
        monkeypatch.setenv("COOKIE_SECURE", "true")
        module = _load_scaffold_routes(monkeypatch)

        app = FastAPI()
        app.include_router(module.router)
        resp = TestClient(app, follow_redirects=False).get("/auth/example/login")

        assert module.COOKIE_SECURE is True
        assert "Secure" in resp.headers["set-cookie"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeRequest:
    def __init__(self, cookies):
        self.cookies = cookies


def _fake_request(cookies: dict):
    return _FakeRequest(cookies)

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


def _stub_full_flow(monkeypatch, routes, user: dict):
    """Mock a provider that answers both the token and userinfo calls."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "tok", "token_type": "bearer"})
        return httpx.Response(200, json=user)

    _install_transport(monkeypatch, routes, handler)


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
