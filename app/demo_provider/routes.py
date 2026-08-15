"""
Demo Provider: a real OAuth 2.0 authorization server, running inside this app.

This exists so you can walk the entire OAuth flow without registering an app
with GitHub, Google, or anyone else. Nothing here is faked: your app really does
redirect to an authorization endpoint, really receives an authorization code,
really exchanges it over HTTP for a token, and really calls a userinfo endpoint
with a bearer token. The only difference is that the provider happens to live at
localhost instead of github.com.

That also makes this the one place in the project where you can read the *other*
side of OAuth, what the provider does with your request:

  GET  /demo-provider/authorize , validate the request, show a consent screen
  GET  /demo-provider/approve   , issue an authorization code, redirect back
  POST /demo-provider/token     , verify the code (+ secret or PKCE), issue a token
  GET  /demo-provider/userinfo  , verify the bearer token, return the profile
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/demo-provider", tags=["demo-provider"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

# Credentials for the demo. A real provider would generate these when you
# register an application; here they are fixed so the demo needs no setup.
DEMO_CLIENT_ID = "demo-client-id"
DEMO_CLIENT_SECRET = "demo-client-secret"

# The user who "logs in". A real provider would look this up after the user
# authenticates; the demo skips authentication and always returns Ada.
DEMO_USER = {
    "user_id": "1815",
    "display_name": "Ada Lovelace",
    "email_address": "ada@example.com",
    "avatar": "https://api.dicebear.com/7.x/thumbs/svg?seed=ada",
    "note": "This profile is served by the local demo provider, not a real service.",
}

# Issued codes and tokens. Short-lived and single-use, like the real thing.
_codes: dict[str, dict] = {}
_tokens: dict[str, dict] = {}

CODE_TTL = 300     # 5 minutes, same ballpark as real providers
TOKEN_TTL = 3600


def _sweep() -> None:
    now = time.time()
    for code in [c for c, d in _codes.items() if now - d["born"] > CODE_TTL]:
        _codes.pop(code, None)
    for token in [t for t, d in _tokens.items() if now - d["born"] > TOKEN_TTL]:
        _tokens.pop(token, None)


def _error(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": "invalid_request", "error_description": message}, status_code=status)


@router.get("/authorize", response_class=HTMLResponse)
async def authorize(
    request: Request,
    client_id: str = "",
    redirect_uri: str = "",
    scope: str = "",
    state: str = "",
    response_type: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "",
):
    """
    Step 1, from the provider's side.

    A real provider would make you sign in here. We skip that and go straight to
    the consent screen, but everything else is checked exactly as a real
    authorization server would check it.
    """
    if client_id != DEMO_CLIENT_ID:
        return _error(f"Unknown client_id: {client_id!r}")
    if response_type != "code":
        return _error(f"Unsupported response_type: {response_type!r}. Expected 'code'.")
    if not redirect_uri:
        return _error("Missing redirect_uri.")

    return templates.TemplateResponse(
        "demo_consent.html",
        {
            "request": request,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "scopes": [s for s in scope.split(" ") if s],
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "user": DEMO_USER,
        },
    )


@router.get("/approve")
async def approve(
    redirect_uri: str = "",
    state: str = "",
    scope: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "",
):
    """The user clicked Authorize. Issue a code and send them back."""
    _sweep()

    code = secrets.token_urlsafe(24)
    _codes[code] = {
        "born": time.time(),
        "scope": scope,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }

    params = {"code": code}
    if state:
        params["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}", status_code=303)


@router.get("/deny")
async def deny(redirect_uri: str = "", state: str = ""):
    """The user clicked Cancel. Real providers report this as an error."""
    params = {"error": "access_denied", "error_description": "The user declined the request."}
    if state:
        params["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}", status_code=303)


@router.post("/token")
async def token(
    grant_type: str = Form(""),
    code: str = Form(""),
    redirect_uri: str = Form(""),
    client_id: str = Form(""),
    client_secret: str = Form(""),
    code_verifier: str = Form(""),
):
    """
    Step 3, from the provider's side, where the app proves who it is.

    Note what is being checked, because this is the part tutorials skip: the code
    must exist, be unused, and be unexpired; the redirect_uri must match the one
    the code was issued for; and the client must prove itself with either the
    client secret or a PKCE verifier.
    """
    _sweep()

    if grant_type != "authorization_code":
        return _error(f"Unsupported grant_type: {grant_type!r}")
    if client_id != DEMO_CLIENT_ID:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Unknown client_id."},
            status_code=401,
        )

    entry = _codes.pop(code, None)  # single use: popped whether or not it validates
    if entry is None:
        return JSONResponse(
            {
                "error": "bad_verification_code",
                "error_description": (
                    "The authorization code is invalid, expired, or was already used. "
                    "Codes may be exchanged exactly once."
                ),
            },
            status_code=400,
        )

    if redirect_uri != entry["redirect_uri"]:
        return JSONResponse(
            {
                "error": "redirect_uri_mismatch",
                "error_description": (
                    "redirect_uri must be identical to the one used in the authorization "
                    f"request. Expected {entry['redirect_uri']!r}, got {redirect_uri!r}."
                ),
            },
            status_code=400,
        )

    # PKCE, when the authorization request used it
    challenge = entry.get("code_challenge")
    if challenge:
        if not code_verifier:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "This flow used PKCE, so code_verifier is required.",
                },
                status_code=400,
            )
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        if not secrets.compare_digest(expected, challenge):
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "SHA256(code_verifier) did not match code_challenge.",
                },
                status_code=400,
            )

    # Confidential clients must still present the secret, PKCE or not.
    if not secrets.compare_digest(client_secret or "", DEMO_CLIENT_SECRET):
        return JSONResponse(
            {
                "error": "invalid_client",
                "error_description": (
                    "client_secret is missing or wrong. PKCE does not replace the secret "
                    "for confidential clients, it is sent in addition to it."
                ),
            },
            status_code=401,
        )

    access_token = secrets.token_urlsafe(32)
    _tokens[access_token] = {"born": time.time(), "scope": entry["scope"]}

    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": TOKEN_TTL,
            "scope": entry["scope"],
        }
    )


@router.get("/userinfo")
async def userinfo(request: Request):
    """
    Step 4, from the provider's side.

    The field names here are deliberately unlike any other provider's. That is
    the point of the normalize step in your app.
    """
    _sweep()

    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return JSONResponse(
            {"error": "invalid_token", "error_description": "Expected an Authorization: Bearer header."},
            status_code=401,
        )

    presented = header.split(" ", 1)[1].strip()
    entry = _tokens.get(presented)
    if entry is None:
        return JSONResponse(
            {"error": "invalid_token", "error_description": "Unknown or expired access token."},
            status_code=401,
        )

    return JSONResponse(dict(DEMO_USER))
