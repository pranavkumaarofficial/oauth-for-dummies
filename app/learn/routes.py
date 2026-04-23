"""
Learn Mode Routes — the interactive OAuth debugger.

Two pages:
  GET /learn/{provider}/start   — shows Step 1 (auth URL construction)
  GET /learn/{provider}/result  — shows Steps 2-5 with captured data
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.storage import store
from app.config import settings
from providers.registry import get_provider

router = APIRouter(prefix="/learn", tags=["learn"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


@router.get("/{provider_name}/start", response_class=HTMLResponse)
async def learn_start(provider_name: str, request: Request, state: str = ""):
    """Pre-flight page — shows how the authorization URL is built."""
    preflight = store.get_learn_preflight(state)
    if not preflight:
        return RedirectResponse(url="/")

    try:
        provider = get_provider(provider_name)
    except ValueError:
        return RedirectResponse(url="/")

    return templates.TemplateResponse(
        "learn_start.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "provider_name": provider_name,
            "provider_display": provider.display_name,
            "provider_icon": provider.icon,
            "authorize_url": preflight["base_url"],
            "params": preflight["params"],
            "full_url": preflight["url"],
            "state": state,
        },
    )


@router.get("/{provider_name}/result", response_class=HTMLResponse)
async def learn_result(provider_name: str, request: Request):
    """Post-callback page — shows all steps with real captured data."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/")

    debug = store.get_debug_session(session_id)
    if not debug:
        return RedirectResponse(url="/profile")

    return templates.TemplateResponse(
        "learn_result.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "debug": debug,
            "provider_name": provider_name,
        },
    )
