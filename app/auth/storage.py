"""
Token Storage — keeps track of logged-in users.

This is a simple in-memory + JSON file store for learning purposes.
In production, you'd use a database (PostgreSQL, Redis, etc.).

This is NOT production-ready. It's designed to be readable.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path


STORAGE_FILE = Path(__file__).resolve().parent.parent.parent / ".tokens.json"


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


@dataclass
class DebugSession:
    """Captured data from a learn-mode OAuth flow for the debugger UI."""

    session_id: str
    provider: str

    # Step 1: Authorization URL construction
    authorize_url: str = ""
    authorize_params: dict = field(default_factory=dict)
    full_authorize_url: str = ""

    # Step 2: Callback received
    callback_code: str = ""
    callback_state: str = ""

    # Step 3: Token exchange
    token_request_url: str = ""
    token_request_body: dict = field(default_factory=dict)
    token_response_raw: dict = field(default_factory=dict)
    token_type: str = ""
    token_scope: str = ""

    # Step 4: User info fetch
    userinfo_request_url: str = ""
    userinfo_request_headers: dict = field(default_factory=dict)
    userinfo_response_raw: dict = field(default_factory=dict)

    # Step 5: Normalized profile
    user_id: str = ""
    user_name: str = ""
    user_email: str | None = None
    user_avatar: str | None = None

    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()


class TokenStore:
    """
    Dead-simple session storage.

    Stores sessions in memory and optionally persists to a JSON file.
    """

    def __init__(self):
        self._sessions: dict[str, StoredSession] = {}
        self._states: dict[str, str] = {}  # state -> provider name
        self._state_modes: dict[str, str] = {}  # state -> "learn" or "quick"
        self._debug_sessions: dict[str, DebugSession] = {}
        self._learn_preflights: dict[str, dict] = {}  # state -> auth URL details

    def save_state(self, state: str, provider_name: str, mode: str = "quick") -> None:
        """Remember the state token so we can verify it on callback."""
        self._states[state] = provider_name
        self._state_modes[state] = mode

    def verify_state(self, state: str) -> str | None:
        """
        Check if the state token is valid and return the provider name.
        Returns None if the state is unknown (possible CSRF attack!).
        """
        return self._states.pop(state, None)

    def get_state_mode(self, state: str) -> str:
        """Get the mode for a state token. Returns 'quick' if not found."""
        return self._state_modes.pop(state, "quick")

    # ---- Learn mode preflight ----

    def save_learn_preflight(self, state: str, details: dict) -> None:
        """Store pre-flight auth URL details for the learn start page."""
        self._learn_preflights[state] = details

    def get_learn_preflight(self, state: str) -> dict | None:
        """Get pre-flight details for display."""
        return self._learn_preflights.get(state)

    def cleanup_learn_preflight(self, state: str) -> None:
        """Remove preflight data after the flow completes."""
        self._learn_preflights.pop(state, None)

    # ---- Debug sessions (learn mode results) ----

    def save_debug_session(self, debug: DebugSession) -> None:
        """Store debug data for learn mode."""
        self._debug_sessions[debug.session_id] = debug

    def get_debug_session(self, session_id: str) -> DebugSession | None:
        """Retrieve debug data by session ID."""
        return self._debug_sessions.get(session_id)

    def delete_debug_session(self, session_id: str) -> None:
        """Clean up debug data."""
        self._debug_sessions.pop(session_id, None)

    # ---- Regular sessions ----

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
        self._debug_sessions.pop(session_id, None)
        self._persist()

    def _persist(self) -> None:
        """Save sessions to disk (for demo purposes)."""
        try:
            data = {k: asdict(v) for k, v in self._sessions.items()}
            STORAGE_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass  # Don't crash if we can't write


# Global store instance — shared across the app
store = TokenStore()
