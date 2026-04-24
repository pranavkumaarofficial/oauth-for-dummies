"""
Base OAuth Provider — the blueprint every provider follows.

Supports both OAuth 2.0 (client_secret) and OAuth 2.1 (PKCE).
To add a new provider, just subclass this and fill in the URLs.
Set use_pkce = True to enable PKCE (Proof Key for Code Exchange).
See github.py for a working example.
"""

from __future__ import annotations

import hashlib
import base64
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx


@dataclass
class OAuthToken:
    """Holds the token data returned by the provider."""

    access_token: str
    token_type: str = "bearer"
    scope: str = ""
    refresh_token: str | None = None
    expires_in: int | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class UserInfo:
    """Normalized user profile — same shape regardless of provider."""

    id: str
    name: str
    email: str | None = None
    avatar: str | None = None
    provider: str = ""
    raw: dict = field(default_factory=dict)


class OAuthProvider(ABC):
    """
    Base class for all OAuth 2.0 providers.

    Subclass this, set the class-level URLs, and implement
    `normalize_userinfo()`. The base class handles the rest:
    building auth URLs, exchanging codes for tokens, fetching user info.
    """

    # ---- Override these in your provider ----
    name: str = ""                  # e.g. "github"
    display_name: str = ""          # e.g. "GitHub"
    authorize_url: str = ""         # Provider's authorization endpoint
    token_url: str = ""             # Provider's token endpoint
    userinfo_url: str = ""          # Provider's user info API
    default_scopes: list[str] = []  # Default scopes to request
    icon: str = ""                  # Emoji or icon class for UI
    use_pkce: bool = False          # Set True for OAuth 2.1 / PKCE flow

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    # ---- PKCE helpers (OAuth 2.1) ----

    @staticmethod
    def _generate_code_verifier() -> str:
        """Generate a cryptographic random code verifier (43-128 chars)."""
        return secrets.token_urlsafe(64)

    @staticmethod
    def _generate_code_challenge(verifier: str) -> str:
        """Create S256 code challenge from verifier."""
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def get_authorization_url(self, state: str | None = None) -> tuple[str, str]:
        """
        Build the URL to redirect the user to for authorization.

        Returns:
            (url, state) — the full URL and the state token for CSRF protection.

        If use_pkce is True, also returns code_verifier as third element.
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.default_scopes),
            "state": state,
            "response_type": "code",
        }

        code_verifier = None
        if self.use_pkce:
            code_verifier = self._generate_code_verifier()
            code_challenge = self._generate_code_challenge(code_verifier)
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        url = f"{self.authorize_url}?{urlencode(params)}"

        print(f"\n{'='*60}")
        print(f"  STEP 1 — Redirect user to {self.display_name}")
        print(f"{'='*60}")
        print(f"  URL: {self.authorize_url}")
        print(f"  client_id:    {self.client_id[:8]}...")
        print(f"  redirect_uri: {self.redirect_uri}")
        print(f"  scope:        {' '.join(self.default_scopes)}")
        print(f"  state:        {state[:16]}...")
        if self.use_pkce:
            print(f"  PKCE:         enabled (S256)")
            print(f"  verifier:     {code_verifier[:16]}...")
            print(f"  challenge:    {code_challenge[:16]}...")
        print(f"{'='*60}\n")

        if self.use_pkce:
            return url, state, code_verifier
        return url, state

    async def exchange_code_for_token(self, code: str, code_verifier: str | None = None) -> OAuthToken:
        """
        Exchange the authorization code for an access token.

        This is the POST request your app makes server-to-server.
        The user never sees this — it happens in the background.

        If PKCE is enabled, pass code_verifier instead of using client_secret.
        """
        data = {
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        if code_verifier or self.use_pkce:
            data["code_verifier"] = code_verifier
        else:
            data["client_secret"] = self.client_secret

        print(f"\n{'='*60}")
        print(f"  STEP 3 — Exchange code for token")
        print(f"{'='*60}")
        print(f"  POST {self.token_url}")
        print(f"  code:   {code[:16]}...")
        if code_verifier:
            print(f"  PKCE:   code_verifier={code_verifier[:16]}...")
        else:
            print(f"  secret: {self.client_secret[:4]}{'*' * 12}")
        print(f"{'='*60}\n")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            raw = response.json()

        token = OAuthToken(
            access_token=raw["access_token"],
            token_type=raw.get("token_type", "bearer"),
            scope=raw.get("scope", ""),
            refresh_token=raw.get("refresh_token"),
            expires_in=raw.get("expires_in"),
            raw=raw,
        )

        print(f"  Got access token: {token.access_token[:12]}...")
        print(f"  Token type: {token.token_type}")
        print(f"  Scope: {token.scope}\n")

        return token

    async def get_userinfo(self, token: OAuthToken) -> UserInfo:
        """
        Use the access token to fetch the user's profile.

        This is the "payoff" — the whole reason we did OAuth.
        """
        print(f"\n{'='*60}")
        print(f"  STEP 4 — Fetch user info from {self.display_name}")
        print(f"{'='*60}")
        print(f"  GET {self.userinfo_url}")
        print(f"  Authorization: Bearer {token.access_token[:12]}...")
        print(f"{'='*60}\n")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {token.access_token}"},
            )
            response.raise_for_status()
            raw = response.json()

        user = self.normalize_userinfo(raw)
        user.provider = self.name
        user.raw = raw

        print(f"  Got user info:")
        print(f"     Name:   {user.name}")
        print(f"     Email:  {user.email or 'not provided'}")
        print(f"     Avatar: {user.avatar[:40] + '...' if user.avatar else 'none'}\n")

        return user

    @abstractmethod
    def normalize_userinfo(self, raw: dict[str, Any]) -> UserInfo:
        """
        Convert provider-specific user data into our standard UserInfo.

        Every provider returns user data in a different shape.
        This method maps their format to ours.
        """
        ...

    # ---- Detailed methods for Learn Mode debugger ----

    def get_authorization_url_detailed(self, state: str | None = None) -> dict:
        """Like get_authorization_url, but returns all intermediate data."""
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.default_scopes),
            "state": state,
            "response_type": "code",
        }

        code_verifier = None
        if self.use_pkce:
            code_verifier = self._generate_code_verifier()
            code_challenge = self._generate_code_challenge(code_verifier)
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        url = f"{self.authorize_url}?{urlencode(params)}"

        print(f"\n{'='*60}")
        print(f"  STEP 1 — Redirect user to {self.display_name}")
        print(f"{'='*60}")
        print(f"  URL: {self.authorize_url}")
        print(f"  client_id:    {self.client_id[:8]}...")
        print(f"  redirect_uri: {self.redirect_uri}")
        print(f"  scope:        {' '.join(self.default_scopes)}")
        print(f"  state:        {state[:16]}...")
        if self.use_pkce:
            print(f"  PKCE:         enabled (S256)")
            print(f"  verifier:     {code_verifier[:16]}...")
            print(f"  challenge:    {code_challenge[:16]}...")
        print(f"{'='*60}\n")

        # Redact client_id for display
        display_params = dict(params)
        display_params["client_id"] = self.client_id[:8] + "..."

        result = {
            "url": url,
            "state": state,
            "params": display_params,
            "base_url": self.authorize_url,
            "use_pkce": self.use_pkce,
        }
        if self.use_pkce:
            result["code_verifier"] = code_verifier
        return result

    async def exchange_code_for_token_detailed(self, code: str, code_verifier: str | None = None) -> dict:
        """Like exchange_code_for_token, but captures request/response data."""
        data = {
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        if code_verifier or self.use_pkce:
            data["code_verifier"] = code_verifier
        else:
            data["client_secret"] = self.client_secret

        print(f"\n{'='*60}")
        print(f"  STEP 3 — Exchange code for token")
        print(f"{'='*60}")
        print(f"  POST {self.token_url}")
        print(f"  code:   {code[:16]}...")
        if code_verifier:
            print(f"  PKCE:   code_verifier={code_verifier[:16]}...")
        else:
            print(f"  secret: {self.client_secret[:4]}{'*' * 12}")
        print(f"{'='*60}\n")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            raw = response.json()

        token = OAuthToken(
            access_token=raw["access_token"],
            token_type=raw.get("token_type", "bearer"),
            scope=raw.get("scope", ""),
            refresh_token=raw.get("refresh_token"),
            expires_in=raw.get("expires_in"),
            raw=raw,
        )

        print(f"  Got access token: {token.access_token[:12]}...")
        print(f"  Token type: {token.token_type}")
        print(f"  Scope: {token.scope}\n")

        # Redacted versions for UI display
        display_body = {
            "client_id": self.client_id[:8] + "...",
            "code": code[:16] + "...",
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        if code_verifier:
            display_body["code_verifier"] = code_verifier[:16] + "..."
        else:
            display_body["client_secret"] = self.client_secret[:4] + "************"

        display_response = {
            "access_token": token.access_token[:12] + "...",
            "token_type": token.token_type,
            "scope": token.scope,
        }
        if token.expires_in:
            display_response["expires_in"] = token.expires_in

        return {
            "token": token,
            "request_url": self.token_url,
            "request_body": display_body,
            "response_raw": display_response,
        }

    async def get_userinfo_detailed(self, token: OAuthToken) -> dict:
        """Like get_userinfo, but captures request/response data."""
        print(f"\n{'='*60}")
        print(f"  STEP 4 — Fetch user info from {self.display_name}")
        print(f"{'='*60}")
        print(f"  GET {self.userinfo_url}")
        print(f"  Authorization: Bearer {token.access_token[:12]}...")
        print(f"{'='*60}\n")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {token.access_token}"},
            )
            response.raise_for_status()
            raw = response.json()

        user = self.normalize_userinfo(raw)
        user.provider = self.name
        user.raw = raw

        print(f"  Got user info:")
        print(f"     Name:   {user.name}")
        print(f"     Email:  {user.email or 'not provided'}")
        print(f"     Avatar: {user.avatar[:40] + '...' if user.avatar else 'none'}\n")

        return {
            "user": user,
            "request_url": self.userinfo_url,
            "request_headers": {
                "Authorization": f"Bearer {token.access_token[:12]}...",
            },
            "response_raw": raw,
        }
