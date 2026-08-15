"""
Microsoft OAuth Provider: uses Microsoft Identity Platform (v2.0).

Microsoft's OAuth works with personal accounts (Outlook, Xbox),
work/school accounts (Azure AD), or both. Uses the "common"
tenant for maximum compatibility.
"""

from __future__ import annotations

from typing import Any

from providers.base import OAuthProvider, UserInfo


class MicrosoftProvider(OAuthProvider):
    name = "microsoft"
    display_name = "Microsoft"
    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M0 0h11.377v11.377H0zm12.623 0H24v11.377H12.623zM0 12.623h11.377V24H0zm12.623 0H24V24H12.623z"/></svg>'
    authorize_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    userinfo_url = "https://graph.microsoft.com/v1.0/me"
    default_scopes = ["openid", "email", "profile", "User.Read"]

    setup_url = "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps"
    setup_steps = [
        "App registrations, New registration.",
        "Under Supported account types, pick the option that includes personal accounts "
        "unless you only want your own tenant.",
        "Set the Redirect URI platform to Web and paste the callback URL below.",
        "Copy the Application (client) ID from Overview.",
        "Certificates and secrets, New client secret, then copy the Value into your .env.",
    ]
    gotcha = (
        "Copy the secret Value, not the Secret ID. They sit next to each other and the ID "
        "looks plausible. The Value is only shown once."
    )

    def normalize_userinfo(self, raw: dict[str, Any]) -> UserInfo:
        """
        Microsoft Graph returns: {id, displayName, mail, userPrincipalName, ...}
        We map it to our standard shape.
        """
        return UserInfo(
            id=str(raw["id"]),
            name=raw.get("displayName") or "Unknown",
            email=raw.get("mail") or raw.get("userPrincipalName"),
            avatar=None,  # Graph API requires a separate call for photos
        )
