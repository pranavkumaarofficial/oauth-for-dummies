"""
Demo Provider — points at the OAuth server running inside this app.

Nothing about the client side is special: this is an ordinary OAuthProvider
subclass, identical in shape to github.py. The only difference is that its
endpoints resolve to localhost, so you can walk the whole flow without
registering an application anywhere.

PKCE is enabled here so the demo exercises it end to end. Note that the demo is
still a *confidential* client — it sends the client secret as well as the PKCE
verifier, which is what real web apps must do.
"""

from __future__ import annotations

from typing import Any

from providers.base import OAuthProvider, UserInfo


class DemoProvider(OAuthProvider):
    name = "demo"
    display_name = "Demo Provider"
    icon = (
        '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">'
        '<path d="M11 7V5a3 3 0 0 0-6 0v2"/>'
        '<rect x="3.25" y="7" width="9.5" height="6.5" rx="1.5" fill="currentColor" stroke="none"/>'
        "</svg>"
    )
    default_scopes = ["profile", "email"]
    use_pkce = True

    # Filled in by the registry, which knows the app's base URL.
    authorize_url = ""
    token_url = ""
    userinfo_url = ""

    def normalize_userinfo(self, raw: dict[str, Any]) -> UserInfo:
        """
        The demo provider returns user_id / display_name / email_address.

        No other provider uses those names — that is deliberate. It shows why
        this normalize step has to exist at all.
        """
        return UserInfo(
            id=str(raw.get("user_id", "")),
            name=raw.get("display_name") or "Unknown",
            email=raw.get("email_address"),
            avatar=raw.get("avatar"),
        )
