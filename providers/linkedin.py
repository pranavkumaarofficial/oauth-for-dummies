"""
LinkedIn OAuth Provider — uses OpenID Connect.

LinkedIn migrated to OpenID Connect in 2023. The new API
uses standard OIDC scopes and the userinfo endpoint instead
of the old proprietary v2 API.
"""

from __future__ import annotations

from typing import Any

from providers.base import OAuthProvider, UserInfo


class LinkedInProvider(OAuthProvider):
    name = "linkedin"
    display_name = "LinkedIn"
    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'
    authorize_url = "https://www.linkedin.com/oauth/v2/authorization"
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    userinfo_url = "https://api.linkedin.com/v2/userinfo"
    default_scopes = ["openid", "profile", "email"]

    def normalize_userinfo(self, raw: dict[str, Any]) -> UserInfo:
        """
        LinkedIn OIDC returns: {sub, name, email, picture, ...}
        We map it to our standard shape.
        """
        return UserInfo(
            id=str(raw.get("sub", "")),
            name=raw.get("name") or "Unknown",
            email=raw.get("email"),
            avatar=raw.get("picture"),
        )
