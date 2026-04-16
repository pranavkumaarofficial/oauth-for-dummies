"""
Tests for OAuth providers.

Run with: pytest tests/ -v
"""

import pytest
from providers.base import OAuthProvider, OAuthToken, UserInfo


# ---- Test the base provider ----

class MockProvider(OAuthProvider):
    """A fake provider for testing."""
    name = "mock"
    display_name = "Mock Provider"
    authorize_url = "https://mock.example.com/authorize"
    token_url = "https://mock.example.com/token"
    userinfo_url = "https://mock.example.com/userinfo"
    default_scopes = ["read", "email"]
    icon = "🧪"

    def normalize_userinfo(self, raw: dict) -> UserInfo:
        return UserInfo(
            id=str(raw["uid"]),
            name=raw["full_name"],
            email=raw.get("email"),
            avatar=raw.get("pic"),
        )


class TestOAuthProvider:
    """Test the base OAuthProvider class."""

    def setup_method(self):
        self.provider = MockProvider(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:8000/auth/mock/callback",
        )

    def test_provider_has_required_fields(self):
        assert self.provider.name == "mock"
        assert self.provider.display_name == "Mock Provider"
        assert self.provider.authorize_url.startswith("https://")
        assert self.provider.token_url.startswith("https://")
        assert self.provider.userinfo_url.startswith("https://")

    def test_get_authorization_url(self):
        url, state = self.provider.get_authorization_url()

        assert "mock.example.com/authorize" in url
        assert "client_id=test-client-id" in url
        assert "redirect_uri=" in url
        assert "scope=read+email" in url
        assert "state=" in url
        assert "response_type=code" in url

        # State should be a non-empty string
        assert len(state) > 10

    def test_authorization_url_with_custom_state(self):
        url, state = self.provider.get_authorization_url(state="my-custom-state")

        assert state == "my-custom-state"
        assert "state=my-custom-state" in url

    def test_state_is_unique_each_time(self):
        _, state1 = self.provider.get_authorization_url()
        _, state2 = self.provider.get_authorization_url()

        assert state1 != state2

    def test_normalize_userinfo(self):
        raw = {
            "uid": 42,
            "full_name": "Test User",
            "email": "test@example.com",
            "pic": "https://example.com/avatar.jpg",
        }
        user = self.provider.normalize_userinfo(raw)

        assert user.id == "42"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.avatar == "https://example.com/avatar.jpg"

    def test_normalize_userinfo_missing_optional_fields(self):
        raw = {"uid": 1, "full_name": "Minimal User"}
        user = self.provider.normalize_userinfo(raw)

        assert user.id == "1"
        assert user.name == "Minimal User"
        assert user.email is None
        assert user.avatar is None


class TestOAuthToken:
    """Test the OAuthToken dataclass."""

    def test_basic_token(self):
        token = OAuthToken(access_token="abc123")
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"
        assert token.refresh_token is None

    def test_full_token(self):
        token = OAuthToken(
            access_token="abc123",
            token_type="Bearer",
            scope="read:user",
            refresh_token="refresh456",
            expires_in=3600,
            raw={"custom_field": "value"},
        )
        assert token.refresh_token == "refresh456"
        assert token.expires_in == 3600
        assert token.raw["custom_field"] == "value"


class TestUserInfo:
    """Test the UserInfo dataclass."""

    def test_basic_user(self):
        user = UserInfo(id="1", name="Alice")
        assert user.id == "1"
        assert user.name == "Alice"
        assert user.email is None
        assert user.provider == ""

    def test_full_user(self):
        user = UserInfo(
            id="42",
            name="Bob",
            email="bob@example.com",
            avatar="https://example.com/bob.jpg",
            provider="github",
        )
        assert user.provider == "github"
        assert user.avatar == "https://example.com/bob.jpg"
