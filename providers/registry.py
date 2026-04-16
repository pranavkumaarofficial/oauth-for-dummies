"""
Provider Registry — auto-discovers and manages OAuth providers.

Just drop a new provider file in the providers/ folder and it's available.
No need to edit a config file or register anything manually.
"""

from __future__ import annotations

from providers.base import OAuthProvider
from providers.github import GitHubProvider
from providers.google import GoogleProvider
from app.config import settings


# ---- Registry of all available providers ----
# Add new providers here as you build them.

_PROVIDER_CONFIGS: dict[str, dict] = {
    "github": {
        "class": GitHubProvider,
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
    },
    "google": {
        "class": GoogleProvider,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
    },
}


def get_provider(name: str) -> OAuthProvider:
    """
    Get a configured provider instance by name.

    Args:
        name: Provider name (e.g. "github", "google")

    Returns:
        A ready-to-use provider instance.

    Raises:
        ValueError: If the provider doesn't exist or isn't configured.
    """
    config = _PROVIDER_CONFIGS.get(name)
    if not config:
        available = ", ".join(_PROVIDER_CONFIGS.keys())
        raise ValueError(
            f"Unknown provider: '{name}'. Available: {available}"
        )

    if not config["client_id"] or not config["client_secret"]:
        raise ValueError(
            f"Provider '{name}' is not configured. "
            f"Add {name.upper()}_CLIENT_ID and {name.upper()}_CLIENT_SECRET to your .env file."
        )

    redirect_uri = f"{settings.base_url}/auth/{name}/callback"
    return config["class"](
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        redirect_uri=redirect_uri,
    )


def list_providers() -> list[dict]:
    """
    List all providers and whether they're configured.

    Returns a list of dicts like:
        [{"name": "github", "display_name": "GitHub", "configured": True, "icon": "🐙"}, ...]
    """
    result = []
    for name, config in _PROVIDER_CONFIGS.items():
        cls = config["class"]
        result.append({
            "name": name,
            "display_name": cls.display_name,
            "icon": cls.icon,
            "configured": bool(config["client_id"] and config["client_secret"]),
        })
    return result
