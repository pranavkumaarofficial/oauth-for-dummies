<p align="center">
  <img src="docs/diagrams/logo.svg" alt="OAuth for Dummies" width="420"/>
</p>

<p align="center">
  <strong>Add "Login with GitHub/Google" to your FastAPI app in one command.</strong>
</p>

<p align="center">
  <a href="#quickstart"><img src="https://img.shields.io/badge/Try_it-30_seconds-brightgreen?style=for-the-badge" alt="Quickstart"/></a>
  <a href="https://pypi.org/project/oauth-for-dummies/"><img src="https://img.shields.io/pypi/v/oauth-for-dummies?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI"/></a>
  <a href="https://github.com/pranavkumaarofficial/oauth-for-dummies/stargazers"><img src="https://img.shields.io/github/stars/pranavkumaarofficial/oauth-for-dummies?style=for-the-badge&logo=github&color=yellow" alt="Stars"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
</p>

---

## The problem

Every time you add "Login with GitHub" to a FastAPI app, you end up:

1. Googling "fastapi oauth2 example" for the 5th time
2. Copy-pasting from 3 different Stack Overflow answers
3. Debugging redirect URIs for 45 minutes
4. Pulling in a 10,000-line auth library for a 50-line feature

## The fix

```bash
pip install oauth-for-dummies
cd your-fastapi-project
oauth-init
```

That drops three files into your project:

| File | What it does |
|------|--------------|
| `oauth_config.py` | Loads GitHub/Google credentials from `.env` |
| `oauth_routes.py` | `/auth/{provider}/login`, `/auth/{provider}/callback`, `/auth/logout` |
| `.env` | Template with all the env vars you need |

Add two lines to your existing app:

```python
from oauth_routes import router as oauth_router
app.include_router(oauth_router)
```

Done. Your users can now log in with GitHub and Google.

---

## Quickstart

```bash
# Install
pip install oauth-for-dummies

# Scaffold into your project
cd my-fastapi-project
oauth-init

# Install deps the generated code needs
pip install fastapi uvicorn httpx python-dotenv

# Add your OAuth keys to .env, then run
uvicorn oauth_example_app:app --reload
```

Open `http://localhost:8000` and click login.

### Don't have OAuth keys yet?

**GitHub:** [github.com/settings/developers](https://github.com/settings/developers) &rarr; New OAuth App &rarr; callback URL: `http://localhost:8000/auth/github/callback`

**Google:** [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials) &rarr; Create OAuth Client ID &rarr; redirect URI: `http://localhost:8000/auth/google/callback`

---

## What you get

### Routes

| Route | What it does |
|-------|--------------|
| `/auth/github/login` | Redirects to GitHub OAuth |
| `/auth/github/callback` | Handles the redirect back |
| `/auth/google/login` | Redirects to Google OAuth |
| `/auth/google/callback` | Handles the redirect back |
| `/auth/logout` | Clears session, redirects home |

### Session helper

```python
from oauth_routes import get_session

@app.get("/dashboard")
async def dashboard(request: Request):
    user = get_session(request)
    if not user:
        return RedirectResponse("/auth/github/login")
    return {"hello": user["name"]}
```

`get_session()` returns a dict with `id`, `name`, `email`, `avatar`, `provider` &mdash; or `None` if not logged in.

### CLI options

```
oauth-init                       # all providers + example app
oauth-init --provider github     # GitHub only
oauth-init --provider google     # Google only
oauth-init --no-example          # skip example app, just the routes + config
oauth-init --dir ./myproject     # target a different directory
```

---

## How OAuth works (the short version)

```
You click "Login with GitHub"
        |
        v
Your app redirects to GitHub's /authorize endpoint
        |
        v
User clicks "Allow" on GitHub
        |
        v
GitHub redirects back to /auth/github/callback?code=abc123
        |
        v
Your app exchanges that code for an access token (server-to-server)
        |
        v
Your app calls GitHub's API with that token to get the user's profile
        |
        v
Session created. User is logged in. No password was ever shared.
```

The generated code is ~150 lines total across two files. No magic. Read it.

---

## Want to understand OAuth deeply?

This repo also includes a full tutorial app with step-by-step logging of every OAuth step:

```bash
git clone https://github.com/pranavkumaarofficial/oauth-for-dummies.git
cd oauth-for-dummies
pip install -r requirements.txt
cp .env.example .env
# add your OAuth keys
uvicorn app.main:app --reload
```

Every step of the OAuth flow gets printed to your terminal with clear labels.

See also:
- [How OAuth Works](docs/how-oauth-works.md) &mdash; visual explainer
- [Step-by-step Tutorial](docs/tutorial.md) &mdash; build it from scratch

---

## Project structure

```
oauth-for-dummies/
|
|-- oauth_for_dummies/           # The pip-installable CLI package
|   |-- cli.py                   # oauth-init command
|   +-- scaffold/                # Files dropped into your project
|       |-- oauth_config.py
|       |-- oauth_routes.py
|       |-- oauth_example_app.py
|       +-- dot_env_example
|
|-- app/                         # Full tutorial app (learning resource)
|   |-- main.py
|   |-- config.py
|   |-- auth/
|   |   |-- routes.py
|   |   +-- storage.py
|   |-- templates/
|   +-- static/
|
|-- providers/                   # OAuth provider implementations
|   |-- base.py                  # OAuthProvider base class
|   |-- github.py
|   |-- google.py
|   +-- registry.py
|
|-- docs/                        # Guides and diagrams
|-- tests/                       # Unit tests
+-- pyproject.toml               # PyPI packaging config
```

---

## Contributing

Want to add a provider? Improve the CLI? Fix something?

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT
