"""
Tests for the oauth-init CLI.

The CLI writes a .env full of client secrets into someone's project, so the
thing most worth testing is that it can never leave that file unignored.

Run with: pytest tests/ -v
"""

from __future__ import annotations

from pathlib import Path

from oauthlens.cli import _protect_env_file


class TestProtectEnvFile:
    """`oauthlens` must not drop a secrets file into an unprotected repo."""

    def test_creates_gitignore_when_missing(self, tmp_path: Path):
        message = _protect_env_file(tmp_path)

        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        assert ".env" in gitignore.read_text()
        assert "create" in message

    def test_appends_to_existing_gitignore(self, tmp_path: Path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("__pycache__/\n*.pyc\n")

        message = _protect_env_file(tmp_path)
        content = gitignore.read_text()

        assert ".env" in content
        assert "__pycache__/" in content  # existing rules survive
        assert "update" in message

    def test_no_duplicate_when_already_ignored(self, tmp_path: Path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# Environment\n.env\n.tokens.json\n")
        before = gitignore.read_text()

        message = _protect_env_file(tmp_path)

        assert gitignore.read_text() == before
        assert message is None

    def test_recognizes_alternative_spellings(self, tmp_path: Path):
        """Don't add a duplicate when a wildcard already covers .env."""
        for spelling in ("*.env", ".env*", "**/.env", ".env/"):
            gitignore = tmp_path / ".gitignore"
            gitignore.write_text(f"{spelling}\n")

            assert _protect_env_file(tmp_path) is None, spelling
            assert gitignore.read_text() == f"{spelling}\n"

    def test_handles_gitignore_without_trailing_newline(self, tmp_path: Path):
        """A file not ending in \\n must not get .env glued onto the last rule."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc")

        _protect_env_file(tmp_path)
        lines = gitignore.read_text().splitlines()

        assert "*.pyc" in lines
        assert ".env" in lines
        assert not any(line.startswith("*.pyc.env") for line in lines)

    def test_is_idempotent(self, tmp_path: Path):
        _protect_env_file(tmp_path)
        first = (tmp_path / ".gitignore").read_text()

        _protect_env_file(tmp_path)
        assert (tmp_path / ".gitignore").read_text() == first
