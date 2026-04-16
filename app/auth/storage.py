"""
Token Storage - keeps track of logged-in users.

Simple in-memory + JSON file store for learning purposes.
In production, use a database (PostgreSQL, Redis, etc.).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict


STORAGE_FILE = Path(__file__).resolve().parent.parent / ".tokens.json"


@dataclass
class StoredSession:
    """A logged-in user session."""

    session_id: str
    provider: str
    access_token: str
    user_id: str
    user_name: str
    user_email: str | None = None
    user_avatar: str | None = None
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()


class TokenStore:
    """Simple session storage. In-memory with optional JSON persistence."""

    def __init__(self):
        self._sessions: dict[str, StoredSession] = {}
        self._states: dict[str, str] = {}  # state -> provider name

    def save_state(self, state: str, provider_name: str) -> None:
        """Remember the state token so we can verify it on callback."""
        self._states[state] = provider_name

    def verify_state(self, state: str) -> str | None:
        """
        Check if the state token is valid and return the provider name.
        Returns None if the state is unknown (possible CSRF attack).
        """
        return self._states.pop(state, None)

    def save_session(self, session: StoredSession) -> None:
        """Store a user session after successful login."""
        self._sessions[session.session_id] = session
        self._persist()
        print(f"  Session saved for {session.user_name} ({session.provider})")

    def get_session(self, session_id: str) -> StoredSession | None:
        """Retrieve a session by its ID."""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        """Delete a session (logout)."""
        self._sessions.pop(session_id, None)
        self._persist()

    def _persist(self) -> None:
        """Save sessions to disk (for demo purposes)."""
        try:
            data = {k: asdict(v) for k, v in self._sessions.items()}
            STORAGE_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass


# Global store instance
store = TokenStore()
