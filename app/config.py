"""
Configuration — loads settings from .env file.
Everything your app needs to know lives here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    """App-wide settings pulled from environment variables."""

    APP_NAME: str = os.getenv("APP_NAME", "OAuth for Dummies")
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")

    # GitHub
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")

    # Google
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Server
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def base_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"


settings = Settings()
