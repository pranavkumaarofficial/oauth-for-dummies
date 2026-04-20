"""
Tests for the auth flow — storage, state verification, sessions.

Run with: pytest tests/ -v
"""

import pytest
from app.auth.storage import TokenStore, StoredSession


class TestTokenStore:
    """Test the in-memory token store."""

    def setup_method(self):
        self.store = TokenStore()

    # ---- State management (CSRF protection) ----

    def test_save_and_verify_state(self):
        self.store.save_state("abc123", "github")
        result = self.store.verify_state("abc123")
        assert result == "github"

    def test_verify_state_is_one_time(self):
        """State tokens should be consumed after verification."""
        self.store.save_state("abc123", "github")
        self.store.verify_state("abc123")
        result = self.store.verify_state("abc123")
        assert result is None

    def test_verify_unknown_state(self):
        result = self.store.verify_state("unknown")
        assert result is None

    def test_multiple_states(self):
        self.store.save_state("state1", "github")
        self.store.save_state("state2", "google")
        assert self.store.verify_state("state1") == "github"
        assert self.store.verify_state("state2") == "google"

    # ---- Session management ----

    def test_save_and_get_session(self):
        session = StoredSession(
            session_id="sess-123",
            provider="github",
            access_token="token-abc",
            user_id="42",
            user_name="Alice",
            user_email="alice@example.com",
        )
        self.store.save_session(session)
        result = self.store.get_session("sess-123")

        assert result is not None
        assert result.user_name == "Alice"
        assert result.provider == "github"

    def test_get_unknown_session(self):
        result = self.store.get_session("nonexistent")
        assert result is None

    def test_delete_session(self):
        session = StoredSession(
            session_id="sess-456",
            provider="google",
            access_token="token-xyz",
            user_id="7",
            user_name="Bob",
        )
        self.store.save_session(session)
        self.store.delete_session("sess-456")
        result = self.store.get_session("sess-456")
        assert result is None

    def test_delete_nonexistent_session(self):
        # Should not raise
        self.store.delete_session("nonexistent")


class TestStoredSession:
    """Test the StoredSession dataclass."""

    def test_auto_timestamp(self):
        session = StoredSession(
            session_id="s1",
            provider="github",
            access_token="t1",
            user_id="1",
            user_name="Test",
        )
        assert session.created_at > 0

    def test_optional_fields(self):
        session = StoredSession(
            session_id="s1",
            provider="github",
            access_token="t1",
            user_id="1",
            user_name="Test",
        )
        assert session.user_email is None
        assert session.user_avatar is None
