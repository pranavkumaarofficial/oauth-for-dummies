"""
GitHub OAuth Provider

GitHub's OAuth is straightforward and well-documented,
making it a good first provider to understand.
"""

from __future__ import annotations

from typing import Any

import httpx

from providers.base import OAuthProvider, OAuthToken, UserInfo


class GitHubProvider(OAuthProvider):
    name = "github"
    display_name = "GitHub"
    icon = ""
    authorize_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    userinfo_url = "https://api.github.com/user"
    default_scopes = ["read:user", "user:email"]

    def normalize_userinfo(self, raw: dict[str, Any]) -> UserInfo:
        """
        GitHub returns: {login, id, name, email, avatar_url, ...}
        We map it to our standard shape.
        """
        return UserInfo(
            id=str(raw["id"]),
            name=raw.get("name") or raw.get("login", "Unknown"),
            email=raw.get("email"),
            avatar=raw.get("avatar_url"),
        )

    async def get_userinfo(self, token: OAuthToken) -> UserInfo:
        """
        Also fetch email if not in public profile.

        GitHub sometimes hides email from the /user endpoint.
        We try /user/emails as a fallback.
        """
        user = await super().get_userinfo(token)

        if not user.email:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "https://api.github.com/user/emails",
                        headers={
                            "Authorization": f"Bearer {token.access_token}"
                        },
                    )
                    if resp.status_code == 200:
                        emails = resp.json()
                        primary = next(
                            (e for e in emails if e.get("primary")), None
                        )
                        if primary:
                            user.email = primary["email"]
                            print(f"  Found email via /user/emails: {user.email}")
            except Exception:
                pass  # Email is optional

        return user
