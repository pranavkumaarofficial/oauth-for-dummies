"""
Discord OAuth Provider.

Discord uses standard OAuth 2.0. Very popular with bot developers
and gaming communities. The API returns user data including
username, discriminator, and avatar hash.
"""

from __future__ import annotations

from typing import Any

from providers.base import OAuthProvider, UserInfo


class DiscordProvider(OAuthProvider):
    name = "discord"
    display_name = "Discord"
    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>'
    authorize_url = "https://discord.com/oauth2/authorize"
    token_url = "https://discord.com/api/oauth2/token"
    userinfo_url = "https://discord.com/api/users/@me"
    default_scopes = ["identify", "email"]

    def normalize_userinfo(self, raw: dict[str, Any]) -> UserInfo:
        """
        Discord returns: {id, username, discriminator, avatar, email, ...}
        We map it to our standard shape.
        """
        avatar_hash = raw.get("avatar")
        user_id = raw["id"]
        avatar_url = None
        if avatar_hash:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"

        display_name = raw.get("global_name") or raw.get("username", "Unknown")

        return UserInfo(
            id=str(user_id),
            name=display_name,
            email=raw.get("email"),
            avatar=avatar_url,
        )
