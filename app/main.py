"""
OAuth for Dummies — Main Application

This is the entry point. Run it with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.auth.routes import router as auth_router
from app.learn.routes import router as learn_router
from app.auth.storage import store
from providers.registry import list_providers

# ---- App setup ----
app = FastAPI(
    title=settings.APP_NAME,
    description="Learn OAuth 2.0 the easy way.",
    version="1.0.0",
)

# Static files & templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Register routes
app.include_router(auth_router)
app.include_router(learn_router)


# ---- Pages ----

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page — shows available login buttons."""
    providers = list_providers()
    session_id = request.cookies.get("session_id")
    user = None
    if session_id:
        session = store.get_session(session_id)
        if session:
            user = {
                "name": session.user_name,
                "email": session.user_email,
                "avatar": session.user_avatar,
                "provider": session.provider,
            }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "providers": providers,
            "user": user,
            "app_name": settings.APP_NAME,
        },
    )


@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    """Profile page — shows user data after login."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Not logged in",
                "message": "You need to login first. Go back to the home page and click a login button.",
                "app_name": settings.APP_NAME,
            },
        )

    session = store.get_session(session_id)
    if not session:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Session expired",
                "message": "Your session has expired. Please login again.",
                "app_name": settings.APP_NAME,
            },
        )

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": {
                "name": session.user_name,
                "email": session.user_email,
                "avatar": session.user_avatar,
                "provider": session.provider,
                "id": session.user_id,
            },
            "app_name": settings.APP_NAME,
        },
    )


# ---- Startup banner ----

@app.on_event("startup")
async def startup():
    providers = list_providers()
    configured = [p for p in providers if p["configured"]]

    print(f"\n{'='*60}")
    print(f"  {settings.APP_NAME}")
    print(f"{'='*60}")
    print(f"  Server:    {settings.base_url}")
    print(f"  Providers: {len(configured)}/{len(providers)} configured")
    for p in providers:
        status = "ready" if p["configured"] else "not configured"
        print(f"    - {p['display_name']}: {status}")
    print(f"{'='*60}")
    print(f"  Open {settings.base_url} in your browser to start!")
    print(f"{'='*60}\n")
