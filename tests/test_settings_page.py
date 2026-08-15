"""
Tests for the Settings page.

The point of this page is that it never lies about configuration, so the tests
mostly check that what it shows is derived from the running app rather than
hardcoded. A stale callback URL here would send people straight into the
redirect_uri mismatch it exists to prevent.

Run with: pytest tests/ -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from providers.registry import describe_providers, _PROVIDER_CONFIGS


@pytest.fixture
def client():
    return TestClient(app)


class TestDescribeProviders:
    def test_every_provider_is_described(self):
        described = {p["name"] for p in describe_providers()}
        assert described == set(_PROVIDER_CONFIGS)

    def test_callback_url_follows_the_running_base_url(self):
        for p in describe_providers():
            assert p["callback_url"] == f"{settings.base_url}/auth/{p['name']}/callback"

    def test_env_var_names_match_what_the_registry_reads(self):
        """
        The page tells people which variables to set. If these drift from the
        names the app actually reads, the instructions silently stop working.
        """
        for p in describe_providers():
            if p["is_demo"]:
                continue
            assert hasattr(settings, p["env_id"]), p["env_id"]
            assert hasattr(settings, p["env_secret"]), p["env_secret"]

    def test_real_providers_carry_setup_notes(self):
        for p in describe_providers():
            if p["is_demo"]:
                continue
            assert p["setup_url"].startswith("https://"), p["name"]
            assert len(p["setup_steps"]) >= 3, p["name"]
            assert p["gotcha"], p["name"]

    def test_demo_needs_no_setup(self):
        demo = next(p for p in describe_providers() if p["name"] == "demo")
        assert demo["configured"] is True
        assert demo["setup_steps"] == []


class TestSettingsPage:
    def test_renders(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert "Connect a provider" in resp.text

    def test_lists_every_real_provider(self, client):
        resp = client.get("/settings")
        for name in _PROVIDER_CONFIGS:
            if name == "demo":
                continue
            display = _PROVIDER_CONFIGS[name]["class"].display_name
            assert display in resp.text, name

    def test_shows_exact_callback_urls(self, client):
        resp = client.get("/settings")
        for p in describe_providers():
            if p["is_demo"]:
                continue
            assert p["callback_url"] in resp.text, p["name"]

    def test_shows_env_var_names(self, client):
        resp = client.get("/settings")
        assert "GITHUB_CLIENT_ID" in resp.text
        assert "GITHUB_CLIENT_SECRET" in resp.text

    def test_never_renders_a_secret(self, client):
        """
        The page reports whether a provider is configured, never the values.
        Anyone who can load it should learn nothing they did not already have.
        """
        secret = "super-secret-value-should-never-appear"
        original = _PROVIDER_CONFIGS["github"]["client_secret"]
        _PROVIDER_CONFIGS["github"]["client_secret"] = secret
        _PROVIDER_CONFIGS["github"]["client_id"] = "id-should-never-appear"
        try:
            body = client.get("/settings").text
            assert secret not in body
            assert "id-should-never-appear" not in body
            assert "configured" in body
        finally:
            _PROVIDER_CONFIGS["github"]["client_secret"] = original
            _PROVIDER_CONFIGS["github"]["client_id"] = ""

    def test_is_read_only(self, client):
        """No write path exists, so a POST must not be routed."""
        assert client.post("/settings").status_code == 405

    def test_reachable_from_every_page(self, client):
        for path in ["/", "/settings"]:
            assert 'href="/settings"' in client.get(path).text, path
