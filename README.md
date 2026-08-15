# OAuth for Dummies

**Learn how OAuth 2.0 actually works by running it, then add OAuth login to your FastAPI app in one command.**

Most OAuth tutorials show you a diagram and some code. This one runs a real
sign-in flow on your machine and shows you every HTTP request as it happens: the
authorization redirect, the callback, the token exchange, the profile call. Real
requests, real responses, with your own credentials or with none at all.

<p>
  <a href="https://pypi.org/project/oauth-for-dummies/"><img src="https://img.shields.io/pypi/v/oauth-for-dummies?style=flat-square&logo=pypi&logoColor=white&label=PyPI" alt="oauth-for-dummies on PyPI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9 and above"/></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="Built for FastAPI"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License"/></a>
</p>

Two things live in this repo:

1. **An OAuth debugger** you run locally. It walks the flow one hop at a time and
   explains what each request is doing and why.
2. **A scaffolder.** `pip install oauth-for-dummies && oauth-init` drops working
   OAuth routes into your FastAPI project. You own the code, there is no runtime
   dependency, and you can read every line.

---

## Try it in thirty seconds

No signup, no OAuth app registration, no credentials.

```bash
git clone https://github.com/pranavkumaarofficial/oauth-for-dummies.git
cd oauth-for-dummies
pip install -e .
uvicorn app.main:app --reload
```

Open http://localhost:8000 and click **Learn Mode** on the Demo Provider.

The demo provider is a real OAuth 2.0 authorization server running inside the
app. It issues real single-use authorization codes, verifies PKCE, and checks
bearer tokens. Nothing is faked. It just happens to live on localhost instead of
github.com, which is why it needs no setup.

---

## What the debugger shows you

Five steps, one at a time, with a diagram that tracks where you are.

| Step | What you see |
|---|---|
| 1. Authorization request | The exact URL your app built, every query parameter explained |
| 2. Callback | The authorization code and state token, and how the state is verified |
| 3. Token exchange | The server-to-server POST, its body, and the token response |
| 4. User info | The raw JSON the provider returned |
| 5. Normalized profile | How your app maps provider-specific fields to one shape |

The part people find most useful is the channel distinction. Steps 1, 2 and 5
travel through the browser and are visible in the address bar. Steps 3 and 4 go
server to server and the browser never sees them. That is the entire reason your
client secret is safe, and the diagram shows it as solid versus dashed lines.

Steps 3 and 4 also report the real round-trip time, so the network hop is
visible rather than theoretical.

---

## Add OAuth to your own app

```bash
pip install oauth-for-dummies
cd your-fastapi-project
oauth-init
```

Then two lines in your app:

```python
from oauth_routes import router as oauth_router

app.include_router(oauth_router)
```

You now have `/auth/{provider}/login`, `/auth/{provider}/callback` and
`/auth/logout`.

`oauth-init` writes four files into your project and adds `.env` to your
`.gitignore` so you do not commit your client secret:

| File | What it is |
|---|---|
| `oauth_config.py` | Provider credentials read from `.env` |
| `oauth_routes.py` | Login, callback, logout, sessions, PKCE |
| `oauth_example_app.py` | A working demo app you can delete |
| `.env` | Template for your keys |

Reading the session in your own routes:

```python
from oauth_routes import get_session

@app.get("/dashboard")
async def dashboard(request: Request):
    user = get_session(request)
    if not user:
        return RedirectResponse("/auth/github/login")
    return {"welcome": user["name"]}
```

`user` is a dict with `id`, `name`, `email`, `avatar` and `provider`.

---

## Supported providers

| Provider | Scopes requested |
|---|---|
| GitHub | `read:user`, `user:email` |
| Google | `openid`, `email`, `profile` |
| Discord | `identify`, `email` |
| Microsoft | `openid`, `email`, `profile`, `User.Read` |
| Spotify | `user-read-email`, `user-read-private` |
| LinkedIn | `openid`, `profile`, `email` |
| Demo Provider | runs locally, needs no credentials |

Only the providers you configure appear in the UI. The **Settings** page at
http://localhost:8000/settings has setup instructions for each one, including
the exact callback URL to paste, which is derived from your running host and
port rather than hardcoded.

---

## What is OAuth 2.0 and how does it work?

OAuth 2.0 is how "Sign in with Google" works. Instead of giving an app your
password, you tell Google to let that app see your name and email. The app never
touches your password. It gets a temporary token instead.

```
  Browser              Your App             Provider
     |                     |                    |
     |---- click login --->|                    |
     |<--- redirect -------|                    |
     |------------------ GET /authorize ------->|
     |                     |    consent screen  |
     |<----------------- 302 ?code=abc ---------|
     |---- ?code=abc ----->|                    |
     |                     |-- POST /token ---->|   server to server,
     |                     |<-- access_token ---|   browser never sees this
     |                     |-- GET /userinfo -->|
     |                     |<-- profile --------|
     |<--- session cookie -|                    |
```

The five terms worth knowing:

| Term | What it means |
|---|---|
| Authorization code | A short-lived, single-use code. Not a token. Useless without your client secret. |
| Access token | The key your app uses to call the provider's API on the user's behalf. |
| State parameter | A random value that prevents CSRF. It must be tied to the browser that started the flow, not just stored on the server. |
| Scope | The permissions you ask for. The user sees these on the consent screen. |
| PKCE | A cryptographic proof that the app finishing the flow is the one that started it. Required in OAuth 2.1. |

Longer explanations: [How OAuth works, visually](docs/how-oauth-works.md) and the
[step-by-step OAuth tutorial](docs/tutorial.md).

---

## Common questions

### Why does my redirect_uri not match?

This is the most common OAuth error there is. The redirect URI you register with
the provider must match the one your app sends exactly: same scheme, same host,
same port, same path, same trailing slash or lack of one. `http://localhost:8000`
and `http://127.0.0.1:8000` are different URIs as far as the provider is
concerned. The Settings page shows the exact string this app sends.

### What is PKCE and do I need it?

PKCE means Proof Key for Code Exchange. Your app generates a random secret, sends
its SHA-256 hash when starting the flow, and sends the original when exchanging
the code. The provider checks they match, which proves the same app finished the
flow that started it.

It is required in OAuth 2.1 and worth enabling. One thing many tutorials get
wrong: for a web app, PKCE is sent **in addition to** your client secret, not
instead of it. Only public clients such as mobile apps and single-page apps,
which have nowhere safe to keep a secret, omit it. Send PKCE alone from a web app
and providers will reject the token request.

### Is the generated code production ready?

It is suitable for internal tools, prototypes and small apps. Before production,
replace the in-memory session store with Redis or your database, serve over
HTTPS, and set `COOKIE_SECURE=true`. For a large application, use a maintained
library such as [Authlib](https://authlib.org/) or
[fastapi-sso](https://github.com/tomasvotava/fastapi-sso). This project is for
understanding what those libraries do.

### Can I use this with Flask or Django?

Not yet. FastAPI only.

### Do I need to understand OAuth to use it?

No. Run `oauth-init`, add your keys, and it works. Learn Mode is there if you
want to know what is happening.

---

## Security

What the generated code does:

- Binds the `state` parameter to a cookie set when the flow starts, so a state
  captured by an attacker cannot be redeemed in someone else's browser. Checking
  only that the state exists server-side leaves you open to login CSRF, where a
  victim ends up signed into the attacker's account.
- Sends PKCE in addition to the client secret for confidential clients.
- Exchanges the code server side, so the secret never reaches the browser.
- Sets `HttpOnly` and `SameSite=Lax` session cookies, with `Secure` available
  through the `COOKIE_SECURE` environment variable.
- Expires sessions and pending states server side rather than trusting the
  cookie's `max-age`, which a client can ignore.
- Escapes provider-supplied values before rendering them. A display name is
  attacker-controlled input and can contain HTML.
- Reads token error responses properly. GitHub returns HTTP 200 with an error
  body, so checking the status code alone is not enough.

What it does not do: token refresh, multi-tenant configuration, SAML, or account
linking. If you need those, use a maintained auth library.

---

## How this compares

| | oauth-for-dummies | fastapi-sso | Authlib | fastapi-users |
|---|---|---|---|---|
| Main purpose | Learning, then scaffolding | Social login plugin | Full OAuth and OIDC library | User management framework |
| Where the code lives | In your repo | In the library | In the library | In the library |
| Interactive debugger | Yes | No | No | No |
| Works with no credentials | Yes | No | No | No |
| Providers | 6 | Many | Many | Several |
| Maintained by | One person | An active project | An active project | An active project |

Use this to understand OAuth and to get a working flow quickly. Use one of the
others when you want a dependency somebody else maintains.

---

## Project layout

```
oauth_for_dummies/     the pip package, oauth-init and the scaffold templates
app/                   the tutorial app: Learn Mode, settings, demo provider
providers/             one file per provider, each carrying its own setup notes
tests/                 82 tests
docs/                  written guides
```

Running the tests:

```bash
pip install -e . && pytest -q
```

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

Useful things to pick up:

- A new provider such as Twitch, Apple, GitLab or Facebook
- Flask support in the scaffolder
- Hosting the demo publicly so it can be tried without cloning
- Token refresh handling

---

## License

MIT. Use it, learn from it, build on it.
