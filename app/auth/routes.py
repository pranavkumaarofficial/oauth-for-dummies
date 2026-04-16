"""
Auth Routes - handles the OAuth login flow.

Two routes per provider:
  1. GET /auth/{provider}/login    - redirects user to the provider
  2. GET /auth/{provider}/callback - handles the redirect back

Plus:
  GET /auth/logout - clears the session
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from providers.registry import get_provider
from app.auth.storage import store, StoredSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/{provider_name}/login")
async def login(provider_name: str, request: Request):
    """
    Start the OAuth flow.

    Creates a state token (CSRF protection), builds the authorization URL,
    and redirects the user to the provider's login page.
    """
    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    auth_url, state = provider.get_authorization_url()

    # Remember the state so we can verify it when the user comes back
    store.save_state(state, provider_name)

    print(f"\n  Redirecting user to {provider.display_name}...\n")
    return RedirectResponse(url=auth_url)


@router.get("/{provider_name}/callback")
async def callback(provider_name: str, request: Request, code: str = "", state: str = ""):
    """
    Handle the callback from the provider.

    Verifies the state token, exchanges the code for an access token,
    fetches the user's profile, creates a session, and redirects to profile.
    """
    # Verify state (CSRF protection)
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

    print(f"\n{'='*60}")
    print(f"  STEP 2: Callback received from {provider_name}")
    print(f"{'='*60}")
    print(f"  code:  {code[:16]}...")
    print(f"  state: {state[:16]}... verified")
    print(f"{'='*60}\n")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received.")

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Exchange code for token
    try:
        token = await provider.exchange_code_for_token(code)
    except Exception as e:
        print(f"  Token exchange failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code for token: {e}",
        )

    # Fetch user info
    try:
        user = await provider.get_userinfo(token)
    except Exception as e:
        print(f"  Failed to fetch user info: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch user info: {e}",
        )

    # Create session
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

    print(f"\n  Login complete! Welcome, {user.name}!\n")

    response = RedirectResponse(url="/profile", status_code=303)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=3600,  # 1 hour
        samesite="lax",
    )
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
