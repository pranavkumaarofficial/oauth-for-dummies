# I built an OAuth debugger for FastAPI because every tutorial made it harder than it needed to be

Adding "Login with GitHub" to a FastAPI app should be a 20-minute task. It took me an entire afternoon the first time I tried.

The OAuth 2.0 spec is 76 pages. Every tutorial I found used a different approach. Half of them were outdated. And I spent two hours debugging a redirect URI mismatch that turned out to be a trailing slash.

So I built a tool that does two things: drops working OAuth routes into any FastAPI project with one command, and shows you exactly what happens at every step of the flow.

It's called oauth-for-dummies, and it's open source.

GitHub: https://github.com/pranavkumaarofficial/oauth-for-dummies
PyPI: `pip install oauth-for-dummies`

---

## What OAuth actually does

OAuth is the protocol behind every "Login with Google" button. Instead of collecting a user's password, you send them to Google (or GitHub, or Discord). They log in there, Google sends your app a temporary code, and your app exchanges that code for an access token. The token lets you read the user's name and email. Their password never touches your server.

That's the entire Authorization Code flow.

The implementation, though, involves five HTTP requests, three redirect hops, a CSRF token, and provider-specific quirks that no one warns you about. GitHub returns avatar URLs under `avatar_url`. Google uses `picture`. Discord stores avatars as hashes you have to reconstruct into CDN URLs. Microsoft doesn't return avatars from their user endpoint at all.

I kept running into these things. Every provider had some weird edge case, and I'd only discover it after the OAuth flow was already half-built.

---

## The problem with existing libraries

There are good OAuth libraries for Python. Authlib has been around for years. python-social-auth supports dozens of providers. fastapi-oauth2 gives you middleware you can drop in.

But they all share the same design: you install a package, call its API, and auth happens behind a wall. If something breaks (and with OAuth, something always breaks the first time), you're debugging someone else's abstraction.

I wanted to see the actual HTTP requests. What does the token exchange POST body look like? What is the provider sending back? Why is my callback returning a 400?

So I built a tool that generates the code directly into your project. No runtime dependency. You get the files, you own them, you can read every line.

---

## How it works

Install it:

```bash
pip install oauth-for-dummies
```

Run the CLI inside your FastAPI project:

```bash
cd your-project
oauth-init
```

This creates four files:

```
your-project/
  oauth_config.py       # Provider credentials from .env
  oauth_routes.py       # Login, callback, logout endpoints
  oauth_example_app.py  # Working demo app
  .env                  # Template for your OAuth keys
```

Integrate into your existing app with two lines:

```python
from oauth_routes import router as oauth_router

app.include_router(oauth_router)
```

That gives you `/auth/{provider}/login`, `/auth/{provider}/callback`, and `/auth/logout` for every provider you configure.

---

## Six providers, one pattern

The project supports GitHub, Google, Discord, Spotify, Microsoft, and LinkedIn. Each provider follows the same flow but returns data in its own format. The scaffold normalizes everything for you.

Here's the thing that actually ate my time when I was doing this manually. Every provider returns user data differently:

```python
# GitHub returns:  {"id": 123, "name": "...", "avatar_url": "..."}
# Google returns:  {"id": "456", "name": "...", "picture": "..."}
# Discord returns: {"id": "789", "avatar": "a_hash123", ...}
# Spotify returns: {"id": "abc", "display_name": "...", "images": [...]}
# Microsoft returns: {"id": "def", "displayName": "...", "mail": "..."}
# LinkedIn returns: {"sub": "ghi", "name": "...", "picture": "..."}
```

The `_normalize_user` function in the generated routes maps all of these into a consistent shape:

```python
{
    "id": "...",
    "name": "...",
    "email": "...",
    "avatar": "...",
    "provider": "github"  # or "google", "discord", etc.
}
```

You don't have to figure out which field Discord uses for the display name (`global_name` vs `username`) or how to construct a Discord avatar URL from a hash. That's already done.

---

## The OAuth debugger

This is the part I wish existed when I was learning OAuth.

The project includes a tutorial app with a built-in debugger called Learn Mode. Instead of silently redirecting you through the OAuth flow, it pauses at each step and shows you what's happening.

Step 1 is the authorization request. You see the exact URL your app constructs, with every query parameter broken down: `client_id`, `redirect_uri`, `scope`, `state`, `response_type`. If PKCE is enabled, you also see the `code_challenge` and `code_challenge_method`.

Step 2 is the callback. After you authorize with the provider, you see the authorization code and state token your app received. The debugger shows the state verification (CSRF protection) happening in real time.

Step 3 is the token exchange. This is the server-to-server POST request that swaps the authorization code for an access token. You see the request body, the endpoint URL, and the response. Sensitive values like `client_secret` and `access_token` are partially redacted, but visible enough to understand the structure.

Step 4 is the user info request. The GET request to the provider's user info API, with the Bearer token in the Authorization header. You see the raw JSON response, exactly as the provider sent it.

Step 5 is the normalized profile. How your app maps the provider-specific response into the standard user shape.

Each step has an expandable explanation underneath. No JavaScript frameworks, just `<details>` and `<summary>` tags.

To try it yourself:

```bash
git clone https://github.com/pranavkumaarofficial/oauth-for-dummies.git
cd oauth-for-dummies
pip install -e .
cp .env.example .env
# Add at least one provider's credentials to .env
uvicorn app.main:app --reload
# Open http://localhost:8000 and click "Learn Mode"
```

---

## PKCE support (OAuth 2.1)

The project also supports PKCE, which stands for Proof Key for Code Exchange. It's the main security improvement in the OAuth 2.1 draft.

Standard OAuth uses a `client_secret` during the token exchange. This works fine for server-side apps. But mobile apps and SPAs can't safely store a secret in client-side code. PKCE replaces the secret with a cryptographic challenge.

Here's the flow:

1. Your app generates a random string called a `code_verifier` (86 characters).
2. It hashes the verifier with SHA-256 and base64url-encodes the result. That's the `code_challenge`.
3. The challenge goes with the authorization request.
4. The original verifier goes with the token exchange.
5. The provider hashes the verifier and checks it against the stored challenge.

If someone intercepts the authorization code in transit, they can't use it without the verifier. And the challenge from step 3 is a one-way hash, so intercepting that doesn't help either.

Enable PKCE on any provider with one line:

```python
# In the tutorial app
class MyProvider(OAuthProvider):
    use_pkce = True

# In the scaffold
PKCE_PROVIDERS = {"github", "google"}
```

The actual implementation is about 15 lines:

```python
import hashlib
import base64
import secrets

def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)

def _generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
```

The Learn Mode debugger shows PKCE parameters when enabled, so you can see the verifier and challenge values at each step.

---

## Security defaults

The generated code includes security measures that are easy to get wrong when you're implementing OAuth by hand.

The `state` parameter handles CSRF protection. A random token is generated before the redirect and verified on callback. If it doesn't match, the request is rejected. Session IDs are stored in HTTP-only cookies, so JavaScript can't access them. The cookies use `SameSite=Lax` to prevent cross-site request forgery. The client secret never reaches the browser because the code-for-token exchange happens entirely on your server. Sessions expire after one hour by default, but the `max_age` value is configurable.

The session store is in-memory (a Python dict). For production, you'd swap it for Redis or a database. For development, it works without any extra setup.

---

## Getting your OAuth credentials

Each provider has a developer portal where you register your app and get a client ID and secret. The process is roughly the same everywhere: create an app, set the callback URL, copy the credentials.

For GitHub, go to github.com/settings/developers and create an OAuth App. Set the callback URL to `http://localhost:8000/auth/github/callback`.

For Google, go to console.cloud.google.com/apis/credentials. Create an OAuth Client ID for a Web application. The redirect URI is `http://localhost:8000/auth/google/callback`.

Discord is at discord.com/developers/applications. Create an application, go to OAuth2, and add `http://localhost:8000/auth/discord/callback` as a redirect.

Spotify is at developer.spotify.com/dashboard. Create an app and add the redirect URI `http://localhost:8000/auth/spotify/callback`.

For Microsoft, go to portal.azure.com and register an application with the redirect URI `http://localhost:8000/auth/microsoft/callback`.

LinkedIn is at linkedin.com/developers/apps. Create an app, go to the Auth tab, and add `http://localhost:8000/auth/linkedin/callback`.

Copy the Client ID and Client Secret into your `.env` file. Only configure the providers you actually want. Unconfigured ones don't show up in the UI.

---

## When to use this (and when not to)

This is a good fit if you want OAuth working in your FastAPI app quickly, you want to understand what the code is doing, or you're building a prototype or internal tool and don't want a runtime dependency on an auth library.

It's not the right tool if you need 20+ providers, enterprise SSO with SAML, or a production auth system handling millions of sessions. For that, look at Authlib or a managed service like Auth0.

I'm not trying to replace those. oauth-for-dummies fills the gap between "I have no idea how OAuth works" and "I need a production auth system." Most projects start in that gap. I know I did.

---

## Try it

```bash
pip install oauth-for-dummies
oauth-init
```

Or clone the repo and run the tutorial app with the debugger:

```bash
git clone https://github.com/pranavkumaarofficial/oauth-for-dummies.git
cd oauth-for-dummies
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload
```

MIT licensed. If you want to add a provider (Twitter/X, Apple, Facebook, Twitch) or help with Flask support, PRs are open.

GitHub: https://github.com/pranavkumaarofficial/oauth-for-dummies
PyPI: https://pypi.org/project/oauth-for-dummies/
