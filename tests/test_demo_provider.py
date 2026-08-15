"""
Tests for the built-in demo authorization server.

The demo provider is what lets someone try Learn Mode with no credentials, so
it has to behave like a real provider — including refusing the things a real
provider refuses. Those refusals are the teaching material.

Run with: pytest tests/ -v
"""

from __future__ import annotations

import base64
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo_provider.routes import DEMO_CLIENT_ID, DEMO_CLIENT_SECRET, _codes

REDIRECT = "http://localhost:8000/auth/demo/callback"


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def _issue_code(client, challenge: str = "", scope: str = "profile email") -> str:
    """Walk the authorize + approve steps and return the issued code."""
    params = {"redirect_uri": REDIRECT, "state": "st", "scope": scope}
    if challenge:
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    resp = client.get("/demo-provider/approve", params=params)
    location = resp.headers["location"]
    return location.split("code=")[1].split("&")[0]


def _challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class TestAuthorize:
    def test_shows_consent_screen(self, client):
        resp = client.get("/demo-provider/authorize", params={
            "client_id": DEMO_CLIENT_ID,
            "redirect_uri": REDIRECT,
            "scope": "profile email",
            "state": "st",
            "response_type": "code",
        })
        assert resp.status_code == 200
        assert "Authorize this application" in resp.text

    def test_rejects_unknown_client(self, client):
        resp = client.get("/demo-provider/authorize", params={
            "client_id": "someone-else",
            "redirect_uri": REDIRECT,
            "response_type": "code",
        })
        assert resp.status_code == 400

    def test_rejects_wrong_response_type(self, client):
        """Implicit flow is not supported, and saying so is the point."""
        resp = client.get("/demo-provider/authorize", params={
            "client_id": DEMO_CLIENT_ID,
            "redirect_uri": REDIRECT,
            "response_type": "token",
        })
        assert resp.status_code == 400
        assert "response_type" in resp.json()["error_description"]

    def test_deny_reports_access_denied(self, client):
        resp = client.get("/demo-provider/deny", params={"redirect_uri": REDIRECT, "state": "st"})
        assert resp.status_code == 303
        assert "error=access_denied" in resp.headers["location"]


class TestTokenExchange:
    def test_happy_path(self, client):
        code = _issue_code(client)
        resp = client.post("/demo-provider/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": DEMO_CLIENT_ID,
            "client_secret": DEMO_CLIENT_SECRET,
        })
        assert resp.status_code == 200
        assert resp.json()["access_token"]
        assert resp.json()["token_type"] == "bearer"

    def test_code_is_single_use(self, client):
        code = _issue_code(client)
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": DEMO_CLIENT_ID,
            "client_secret": DEMO_CLIENT_SECRET,
        }
        assert client.post("/demo-provider/token", data=payload).status_code == 200

        second = client.post("/demo-provider/token", data=payload)
        assert second.status_code == 400
        assert second.json()["error"] == "bad_verification_code"

    def test_redirect_uri_must_match(self, client):
        code = _issue_code(client)
        resp = client.post("/demo-provider/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:8000/somewhere/else",
            "client_id": DEMO_CLIENT_ID,
            "client_secret": DEMO_CLIENT_SECRET,
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "redirect_uri_mismatch"

    def test_secret_still_required_with_pkce(self, client):
        """
        The bug this project shipped: PKCE does not replace client_secret for a
        confidential client. The demo provider enforces that, so the mistake
        fails loudly here instead of silently working.
        """
        verifier = "a" * 64
        code = _issue_code(client, challenge=_challenge_for(verifier))

        resp = client.post("/demo-provider/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": DEMO_CLIENT_ID,
            "code_verifier": verifier,
            # no client_secret
        })
        assert resp.status_code == 401
        assert resp.json()["error"] == "invalid_client"
        assert "in addition to it" in resp.json()["error_description"]

    def test_pkce_verifier_must_match_challenge(self, client):
        code = _issue_code(client, challenge=_challenge_for("a" * 64))
        resp = client.post("/demo-provider/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": DEMO_CLIENT_ID,
            "client_secret": DEMO_CLIENT_SECRET,
            "code_verifier": "b" * 64,
        })
        assert resp.status_code == 400
        assert "did not match" in resp.json()["error_description"]

    def test_pkce_verifier_required_when_challenge_used(self, client):
        code = _issue_code(client, challenge=_challenge_for("a" * 64))
        resp = client.post("/demo-provider/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": DEMO_CLIENT_ID,
            "client_secret": DEMO_CLIENT_SECRET,
        })
        assert resp.status_code == 400
        assert "code_verifier is required" in resp.json()["error_description"]

    def test_unknown_code_is_rejected(self, client):
        resp = client.post("/demo-provider/token", data={
            "grant_type": "authorization_code",
            "code": "never-issued",
            "redirect_uri": REDIRECT,
            "client_id": DEMO_CLIENT_ID,
            "client_secret": DEMO_CLIENT_SECRET,
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "bad_verification_code"


class TestUserinfo:
    def _token(self, client) -> str:
        code = _issue_code(client)
        resp = client.post("/demo-provider/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": DEMO_CLIENT_ID,
            "client_secret": DEMO_CLIENT_SECRET,
        })
        return resp.json()["access_token"]

    def test_returns_profile_with_valid_token(self, client):
        token = self._token(client)
        resp = client.get("/demo-provider/userinfo", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        body = resp.json()
        # Deliberately unusual field names — this is why normalize exists
        assert body["display_name"] == "Ada Lovelace"
        assert body["email_address"] == "ada@example.com"
        assert "name" not in body and "email" not in body

    def test_rejects_missing_header(self, client):
        assert client.get("/demo-provider/userinfo").status_code == 401

    def test_rejects_unknown_token(self, client):
        resp = client.get("/demo-provider/userinfo", headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401

    def test_rejects_non_bearer_scheme(self, client):
        token = self._token(client)
        resp = client.get("/demo-provider/userinfo", headers={"Authorization": f"Basic {token}"})
        assert resp.status_code == 401


class TestDemoProviderClient:
    def test_registered_and_always_configured(self):
        from providers.registry import list_providers
        demo = next(p for p in list_providers() if p["name"] == "demo")
        assert demo["configured"] is True

    def test_normalizes_the_odd_field_names(self):
        from providers.registry import get_provider
        provider = get_provider("demo")
        user = provider.normalize_userinfo({
            "user_id": "1815",
            "display_name": "Ada Lovelace",
            "email_address": "ada@example.com",
            "avatar": "http://x/a.svg",
        })
        assert (user.id, user.name, user.email) == ("1815", "Ada Lovelace", "ada@example.com")

    def test_uses_pkce(self):
        from providers.registry import get_provider
        assert get_provider("demo").use_pkce is True

    def test_backchannel_urls_skip_dns(self):
        """localhost resolution costs seconds on Windows; loopback is direct."""
        from providers.registry import get_provider
        provider = get_provider("demo")
        assert provider.token_url.startswith("http://127.0.0.1:")
        assert provider.userinfo_url.startswith("http://127.0.0.1:")
        # but the browser-facing URL must stay on the user's host
        assert "127.0.0.1" not in provider.authorize_url
