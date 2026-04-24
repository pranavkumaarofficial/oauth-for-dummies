"""
oauth-for-dummies CLI — add OAuth to your FastAPI project in one command.

Usage:
    oauth-init                          # scaffold with all providers
    oauth-init --provider github        # only GitHub
    oauth-init --provider google        # only Google
    oauth-init --dir ./myproject        # target a specific directory
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SCAFFOLD_DIR = Path(__file__).parent / "scaffold"

PROVIDERS = {
    "github": {
        "name": "GitHub",
        "env_vars": ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"],
        "setup_url": "https://github.com/settings/developers",
        "callback_path": "/auth/github/callback",
    },
    "google": {
        "name": "Google",
        "env_vars": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "setup_url": "https://console.cloud.google.com/apis/credentials",
        "callback_path": "/auth/google/callback",
    },
    "discord": {
        "name": "Discord",
        "env_vars": ["DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET"],
        "setup_url": "https://discord.com/developers/applications",
        "callback_path": "/auth/discord/callback",
    },
    "spotify": {
        "name": "Spotify",
        "env_vars": ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"],
        "setup_url": "https://developer.spotify.com/dashboard",
        "callback_path": "/auth/spotify/callback",
    },
    "microsoft": {
        "name": "Microsoft",
        "env_vars": ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET"],
        "setup_url": "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps",
        "callback_path": "/auth/microsoft/callback",
    },
    "linkedin": {
        "name": "LinkedIn",
        "env_vars": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
        "setup_url": "https://www.linkedin.com/developers/apps",
        "callback_path": "/auth/linkedin/callback",
    },
}

# Files to always copy
CORE_FILES = ["oauth_config.py", "oauth_routes.py"]
EXAMPLE_APP = "oauth_example_app.py"
ENV_TEMPLATE = "dot_env_example"


def main():
    parser = argparse.ArgumentParser(
        prog="oauth-init",
        description="Add OAuth login to your FastAPI app in one command.",
    )
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS.keys()),
        help="Only set up a specific provider (default: all)",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Target directory (default: current directory)",
    )
    parser.add_argument(
        "--no-example",
        action="store_true",
        help="Skip the example app file",
    )
    args = parser.parse_args()

    target = Path(args.dir).resolve()
    if not target.exists():
        print(f"Error: directory '{target}' does not exist.")
        sys.exit(1)

    providers = [args.provider] if args.provider else list(PROVIDERS.keys())

    print()
    print("  oauth-for-dummies")
    print("  " + "=" * 40)
    print()

    # Copy core files
    copied = []
    for filename in CORE_FILES:
        src = SCAFFOLD_DIR / filename
        dest = target / filename
        if dest.exists():
            print(f"  [skip] {filename} (already exists)")
        else:
            shutil.copy2(src, dest)
            copied.append(filename)
            print(f"  [create] {filename}")

    # Copy example app
    if not args.no_example:
        src = SCAFFOLD_DIR / EXAMPLE_APP
        dest = target / EXAMPLE_APP
        if dest.exists():
            print(f"  [skip] {EXAMPLE_APP} (already exists)")
        else:
            shutil.copy2(src, dest)
            copied.append(EXAMPLE_APP)
            print(f"  [create] {EXAMPLE_APP}")

    # Create .env if it doesn't exist
    env_dest = target / ".env"
    if not env_dest.exists():
        shutil.copy2(SCAFFOLD_DIR / ENV_TEMPLATE, env_dest)
        copied.append(".env")
        print(f"  [create] .env")
    else:
        print(f"  [skip] .env (already exists)")

    # Strip unused providers from config if a specific one was chosen
    if args.provider:
        _strip_unused_providers(target / "oauth_config.py", args.provider)

    print()

    if not copied:
        print("  Nothing to do — all files already exist.")
        print()
        return

    # Print setup instructions
    print("  Setup")
    print("  " + "-" * 40)
    for p in providers:
        info = PROVIDERS[p]
        print(f"\n  {info['name']}:")
        print(f"    1. Go to {info['setup_url']}")
        print(f"    2. Create an OAuth app")
        print(f"    3. Set callback URL to:")
        print(f"       http://localhost:8000{info['callback_path']}")
        print(f"    4. Add credentials to .env:")
        for var in info["env_vars"]:
            print(f"       {var}=\"your-value\"")

    print()
    print("  " + "-" * 40)
    print("  Quick start:")
    print()
    print("    pip install fastapi uvicorn httpx python-dotenv")
    print("    # edit .env with your OAuth credentials")
    print("    uvicorn oauth_example_app:app --reload")
    print()
    print("  Or add to your existing app:")
    print()
    print("    from oauth_routes import router as oauth_router")
    print("    app.include_router(oauth_router)")
    print()
    print("  " + "=" * 40)
    print()


def _strip_unused_providers(config_path: Path, keep: str):
    """Remove provider blocks from oauth_config.py that aren't needed."""
    content = config_path.read_text()
    remove = [p for p in PROVIDERS if p != keep]

    for provider in remove:
        # Remove the block starting with the comment and ending with the closing brace
        marker = f"# --- {PROVIDERS[provider]['name']} ---"
        if marker in content:
            start = content.index(marker)
            # Find the next blank line after the block (two newlines)
            # or the next "# ---" marker
            rest = content[start:]
            # Find end of this block: next section marker or end of OAUTH_PROVIDERS
            lines = rest.split("\n")
            end_offset = 0
            in_block = False
            for i, line in enumerate(lines):
                if i == 0:
                    in_block = True
                    continue
                if line.startswith("# ---") or (in_block and line.strip() == "" and i > 1):
                    end_offset = i
                    break
            else:
                end_offset = len(lines)

            block = "\n".join(lines[:end_offset])
            content = content.replace(block + "\n", "")

    config_path.write_text(content)


if __name__ == "__main__":
    main()
