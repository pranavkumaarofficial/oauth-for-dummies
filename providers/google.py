"""
Google OAuth Provider — uses OpenID Connect.

Google adds a layer on top of OAuth 2.0 called OpenID Connect (OIDC).
The main difference: you get an `id_token` with user info baked in,
so you don't always need a separate API call.

For simplicity, we still use the userinfo endpoint here.
"""

from __future__ import annotations

from typing import Any

from providers.base import OAuthProvider, UserInfo


class GoogleProvider(OAuthProvider):
    name = "google"
    display_name = "Google"
    icon = "🔵"
    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    default_scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def normalize_userinfo(self, raw: dict[str, Any]) -> UserInfo:
        """
        Google returns: {id, email, verified_email, name, picture, ...}
        We map it to our standard shape.
        """
        return UserInfo(
            id=str(raw["id"]),
            name=raw.get("name", "Unknown"),
            email=raw.get("email"),
            avatar=raw.get("picture"),
        )
