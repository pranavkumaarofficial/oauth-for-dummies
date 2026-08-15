"""
Auth Routes — handles the OAuth login flow.

Two routes per provider:
  1. GET /auth/{provider}/login    -> redirects user to the provider
  2. GET /auth/{provider}/callback -> handles the redirect back

Plus:
  GET /auth/logout -> clears the session
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from providers.registry import get_provider
from app.config import settings
from app.auth.storage import store, StoredSession, DebugSession, STATE_TTL, SESSION_TTL

router = APIRouter(prefix="/auth", tags=["auth"])

# The state token is also stored in this cookie so the callback can prove that
# the browser finishing the flow is the same one that started it. Checking only
# that the state exists server-side is NOT enough: an attacker who obtains a
# valid state can have a victim's browser redeem it, which logs the victim into
# the attacker's account (login CSRF, RFC 6749 §10.12).
STATE_COOKIE = "oauth_state"


def _set_cookie(response, key: str, value: str, max_age: int):
    """Set a cookie with our standard security flags."""
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,               # not readable from JavaScript
        secure=settings.COOKIE_SECURE,
        max_age=max_age,
        samesite="lax",              # still sent on the provider's redirect back
        path="/",
    )
    return response


def _set_state_cookie(response, state: str):
    """Bind the pending OAuth state to this browser."""
    return _set_cookie(response, STATE_COOKIE, state, STATE_TTL)


@router.get("/{provider_name}/login")
async def login(provider_name: str, request: Request, mode: str = "quick"):
    """
    STEP 1: Start the OAuth flow.

    When the user clicks "Login with GitHub", this route:
    1. Creates a state token (prevents CSRF attacks)
    2. Builds the authorization URL
    3. Redirects the user to the provider's login page

    If mode=learn, redirects to the pre-flight page first.
    """
    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if mode == "learn":
        details = provider.get_authorization_url_detailed()
        state = details["state"]
        code_verifier = details.get("code_verifier")
        store.save_state(state, provider_name, mode="learn", code_verifier=code_verifier)
        store.save_learn_preflight(state, details)
        print(f"\n  Learn mode: showing pre-flight for {provider.display_name}...\n")
        return _set_state_cookie(
            RedirectResponse(
                url=f"/learn/{provider_name}/start?state={state}",
                status_code=303,
            ),
            state,
        )
    else:
        result = provider.get_authorization_url()
        if provider.use_pkce:
            auth_url, state, code_verifier = result
        else:
            auth_url, state = result
            code_verifier = None
        store.save_state(state, provider_name, code_verifier=code_verifier)
        print(f"\n  Redirecting user to {provider.display_name}...\n")
        return _set_state_cookie(RedirectResponse(url=auth_url), state)


@router.get("/{provider_name}/callback")
async def callback(provider_name: str, request: Request, code: str = "", state: str = ""):
    """
    STEP 2-4: Handle the callback from the provider.

    After the user approves, the provider redirects back here with:
    - code: the authorization code (short-lived, one-time use)
    - state: the CSRF protection token we sent earlier

    This route then:
    2. Verifies the state token
    3. Exchanges the code for an access token
    4. Fetches the user's profile
    5. Creates a session and redirects to the profile page
    """
    # ---- Verify state (CSRF protection) ----
    # Check 1: does the state match the cookie we set when this browser started
    # the flow? This is what stops an attacker's captured state from being
    # redeemed in someone else's browser.
    cookie_state = request.cookies.get(STATE_COOKIE)
    if not state or not cookie_state or not secrets.compare_digest(cookie_state, state):
        print("  CSRF check failed! State does not match this browser's login attempt.")
        raise HTTPException(
            status_code=400,
            detail=(
                "State did not match this browser's login attempt. "
                "This could be a CSRF attack. Try logging in again."
            ),
        )

    # Check 2: is it a state we actually issued?
    saved_provider = store.verify_state(state)
    if saved_provider is None:
        print("  CSRF check failed! Unknown state token.")
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter. This could be a CSRF attack. Try logging in again.",
        )
    if saved_provider != provider_name:
        print(f"  State mismatch: expected {saved_provider}, got {provider_name}")
        raise HTTPException(status_code=400, detail="Provider mismatch.")

    # Check if this was a learn-mode flow
    mode = store.get_state_mode(state)
    code_verifier = store.get_code_verifier(state)

    print(f"\n{'='*60}")
    print(f"  STEP 2 — Callback received from {provider_name}")
    print(f"{'='*60}")
    print(f"  code:  {code[:16]}...")
    print(f"  state: {state[:16]}... verified")
    print(f"  mode:  {mode}")
    if code_verifier:
        print(f"  PKCE:  code_verifier present")
    print(f"{'='*60}\n")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received.")

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if mode == "learn":
        return await _handle_learn_callback(provider, provider_name, code, state, code_verifier)
    else:
        return await _handle_quick_callback(provider, provider_name, code, code_verifier)


async def _handle_quick_callback(provider, provider_name: str, code: str, code_verifier: str | None = None):
    """Standard fast login — redirect straight to /profile."""
    try:
        token = await provider.exchange_code_for_token(code, code_verifier=code_verifier)
    except Exception as e:
        print(f"  Token exchange failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code for token: {e}",
        )

    try:
        user = await provider.get_userinfo(token)
    except Exception as e:
        print(f"  Failed to fetch user info: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch user info: {e}",
        )

    session_id = secrets.token_urlsafe(32)
    session = StoredSession(
        session_id=session_id,
        provider=provider_name,
        access_token=token.access_token,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        user_avatar=user.avatar,
    )
    store.save_session(session)

    print(f"\n  Login complete! Welcome, {user.name}\n")

    response = RedirectResponse(url="/profile", status_code=303)
    _set_cookie(response, "session_id", session_id, SESSION_TTL)
    response.delete_cookie(STATE_COOKIE, path="/")
    return response


async def _handle_learn_callback(provider, provider_name: str, code: str, state: str, code_verifier: str | None = None):
    """Learn mode — capture all data and redirect to /learn/{provider}/result."""
    try:
        token_details = await provider.exchange_code_for_token_detailed(code, code_verifier=code_verifier)
    except Exception as e:
        print(f"  Token exchange failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code for token: {e}",
        )

    token = token_details["token"]

    try:
        user_details = await provider.get_userinfo_detailed(token)
    except Exception as e:
        print(f"  Failed to fetch user info: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch user info: {e}",
        )

    user = user_details["user"]

    # Create normal session (user is logged in)
    session_id = secrets.token_urlsafe(32)
    session = StoredSession(
        session_id=session_id,
        provider=provider_name,
        access_token=token.access_token,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        user_avatar=user.avatar,
    )
    store.save_session(session)

    # Get preflight data for Step 1 display
    preflight = store.get_learn_preflight(state) or {}
    store.cleanup_learn_preflight(state)

    # Create debug session with all captured data
    debug = DebugSession(
        session_id=session_id,
        provider=provider_name,
        authorize_url=preflight.get("base_url", ""),
        authorize_params=preflight.get("params", {}),
        full_authorize_url=preflight.get("url", ""),
        callback_code=code[:16] + "...",
        callback_state=state[:16] + "...",
        token_request_url=token_details["request_url"],
        token_request_body=token_details["request_body"],
        token_response_raw=token_details["response_raw"],
        token_type=token.token_type,
        token_scope=token.scope,
        token_ms=token_details.get("elapsed_ms", 0),
        userinfo_request_url=user_details["request_url"],
        userinfo_request_headers=user_details["request_headers"],
        userinfo_response_raw=user_details["response_raw"],
        userinfo_ms=user_details.get("elapsed_ms", 0),
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        user_avatar=user.avatar,
    )
    store.save_debug_session(debug)

    print(f"\n  Learn mode complete! Welcome, {user.name}\n")

    response = RedirectResponse(url=f"/learn/{provider_name}/result", status_code=303)
    _set_cookie(response, "session_id", session_id, SESSION_TTL)
    response.delete_cookie(STATE_COOKIE, path="/")
    return response


@router.get("/logout")
async def logout(request: Request):
    """Clear the session and redirect home."""
    session_id = request.cookies.get("session_id")
    if session_id:
        store.delete_session(session_id)
        print(f"  User logged out (session: {session_id[:8]}...)")

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_id")
    return response
