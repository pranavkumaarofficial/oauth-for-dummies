"""OAuth providers — drop in a new file to add a provider."""

from providers.registry import get_provider, list_providers

__all__ = ["get_provider", "list_providers"]
