# OAuth 2.0 tutorial: from zero to actually understanding it

This assumes you know basic Python and have used `pip install`. No prior auth
knowledge needed.

If you would rather see it than read it, run the app and open Learn Mode. It
walks the same flow with real requests, and the demo provider needs no
credentials at all.

---

## 1. Why OAuth exists

Say you are building an app that shows someone's GitHub repositories. The old
approach was to ask for their GitHub username and password, which is a bad idea
for four separate reasons:

- You are storing someone else's password
- If your app is breached, their GitHub goes with it
- They cannot limit what you can reach
- They cannot revoke you without changing their password and breaking everything
  else

OAuth fixes all four. The user tells GitHub to let your app see their repos, and
your app receives a token: a temporary key that only works for what was allowed.

---

## 2. The four roles

| Role | What it does | In this app |
|---|---|---|
| Resource owner | Owns the data | You, the human |
| Client | Wants access to it | The FastAPI app |
| Authorization server | Verifies the user, issues tokens | GitHub's OAuth server |
| Resource server | Holds the protected data | GitHub's API |

The authorization server and resource server are often the same company, but
they are separate roles, and providers really do split them across different
hostnames.

---

## 3. The flow in plain language

**Your app says "go ask GitHub".**

It builds a URL to GitHub's authorization page and redirects the user there. The
URL carries your app's public ID and the permissions you want.

```
https://github.com/login/oauth/authorize?
  client_id=abc123&
  redirect_uri=http://localhost:8000/auth/github/callback&
  scope=read:user&
  state=random-csrf-token
```

**The user approves.**

GitHub shows a consent screen naming your app and the permissions. The user
clicks Authorize.

**GitHub sends a code back.**

It redirects the user to your app with a short-lived authorization code:

```
http://localhost:8000/auth/github/callback?code=xyz789&state=random-csrf-token
```

This code is not the access token. It is a single-use ticket that expires in
minutes.

**Your app trades the code for a token.**

This request goes server to server. The user never sees it:

```
POST https://github.com/login/oauth/access_token
  client_id=abc123
  client_secret=super_secret
  code=xyz789
```

**Your app uses the token.**

```
GET https://api.github.com/user
Authorization: Bearer ghp_abc123token
```

GitHub returns the profile. Done.

---

## 4. Why the extra step with the code

It is a fair question. Why not have GitHub hand over the token directly?

Because the authorization code travels through the user's browser, sitting in a
URL where it can be logged, shoulder-surfed, or left in browser history. Anyone
who grabs it still cannot use it, because redeeming it requires your
`client_secret`, which never leaves your server.

The access token only ever travels server to server. That split is the whole
design. This is the Authorization Code grant, and it is the right choice for
server-side web apps.

---

## 5. The state parameter, and the mistake almost everyone makes

The `state` parameter prevents login CSRF: an attacker making your browser
finish *their* login, so you end up signed into *their* account on a site you
trust. Everything you then write or upload lands in their account.

Most tutorials, including an earlier version of this one, describe the check
like this:

```python
# Generate a state, store it, compare it on the way back.
saved = store.verify_state(state)
if saved is None:
    raise HTTPException(400, "Invalid state")
```

That is not enough, and the gap is worth understanding because it is subtle.

The server-side set only proves the value was issued to *somebody*. It does not
prove it was issued to *the browser making this request*. So an attacker can
start a login themselves, capture a perfectly valid code and state, send you the
callback URL, and your app will accept it. The state is in the set, so the check
passes.

The fix is to bind the state to the browser that started the flow:

```python
# At /login: remember the state, and put it in a cookie too.
response.set_cookie("oauth_state", state, httponly=True,
                    max_age=600, samesite="lax")

# At /callback: the cookie must match before anything else happens.
cookie_state = request.cookies.get("oauth_state")
if not state or not cookie_state or not secrets.compare_digest(cookie_state, state):
    raise HTTPException(400, "State did not match this browser's login attempt")

# Then confirm it is a state we actually issued.
pending = _pending_states.pop(state, None)
if pending is None:
    raise HTTPException(400, "Invalid state")
```

Both checks are needed. The cookie proves same browser. The server-side lookup
proves the value was not invented. This is what
`oauth_for_dummies/scaffold/oauth_routes.py` does, and there is a test asserting
that a state issued to one browser cannot be redeemed by another.

This is not a hypothetical: fastapi-sso shipped the same class of bug and fixed
it in version 0.19.0.

---

## 6. Scopes

Scopes are how you ask for specific permissions instead of blanket access.

| Scope | What it grants |
|---|---|
| `read:user` | Basic profile: name, avatar |
| `user:email` | Email address |
| `repo` | Full repository access |
| `read:org` | Organization membership |

Ask for the minimum you need. Users abandon consent screens that ask for too
much, and a smaller scope limits the damage if your token leaks.

Each provider declares its defaults:

```python
class GitHubProvider(OAuthProvider):
    default_scopes = ["read:user", "user:email"]
```

---

## 7. PKCE

PKCE, Proof Key for Code Exchange, adds a second proof that the app finishing the
flow is the one that started it.

Your app generates a random `code_verifier`, sends its SHA-256 hash as
`code_challenge` when starting the flow, and sends the original verifier when
exchanging the code. The provider checks that hashing the verifier reproduces the
challenge.

The part that trips people up: for a server-side web app, PKCE is sent **in
addition to** your client secret, not instead of it. Web apps are confidential
clients and providers still expect the secret. Only public clients, meaning
mobile apps and single-page apps that have nowhere safe to keep a secret, omit
it. Send PKCE alone from a web app and the token request fails.

PKCE is required in OAuth 2.1. The demo provider in this repo verifies it, so you
can watch it work and watch it fail.

---

## 8. Refresh tokens

Access tokens expire. When one does, you either make the user sign in again or
use a refresh token to get a new one quietly.

```
POST /oauth/token
  grant_type=refresh_token
  refresh_token=your_refresh_token
  client_id=abc123
  client_secret=super_secret
```

Not every provider issues them. Google does. GitHub does not, by default.

This project does not implement refresh, to keep the flow readable, but
`OAuthToken` in `providers/base.py` already carries a `refresh_token` field for
when you add it.

---

## 9. Running it

```bash
git clone https://github.com/pranavkumaarofficial/oauth-for-dummies.git
cd oauth-for-dummies
pip install -e .
uvicorn app.main:app --reload
```

Open http://localhost:8000 and pick the Demo Provider. It needs no credentials
because the authorization server runs inside the app.

For a real provider, the Settings page has per-provider instructions and the
exact callback URL to register.

Every step also prints to your terminal:

```
============================================================
  STEP 1, Redirect user to GitHub
============================================================
  URL: https://github.com/login/oauth/authorize
  client_id:    abc12345...
  redirect_uri: http://localhost:8000/auth/github/callback
  scope:        read:user user:email
  state:        kF9x2mQp...
============================================================
```

---

## 10. Errors you will hit

**redirect_uri mismatch.** The callback URL your app sends has to match what you
registered, exactly. A trailing slash counts. So does `localhost` versus
`127.0.0.1`. The Settings page prints the exact string this app sends.

**invalid_client.** Check `.env` for stray spaces or quotes around the values. On
Microsoft specifically, make sure you copied the secret Value and not the Secret
ID, which sits right next to it and looks just as plausible.

**bad_verification_code.** Authorization codes are single-use and short-lived. If
you refreshed the callback page, the code is already spent. Start again.

**Scope not authorized.** Your OAuth app is not approved for the scope you asked
for. On LinkedIn this usually means the Sign In with LinkedIn product has not
been added on the Products tab.

**access_denied on Google.** While your consent screen is in Testing mode, only
accounts on the Test users list can sign in. Add your own address there.

---

## 11. Where to go next

Add a second provider, Google or Discord, and notice how little changes. The
pattern is the same everywhere, which is the real lesson.

Then read [Authlib](https://authlib.org/) or
[fastapi-sso](https://github.com/tomasvotava/fastapi-sso). Now that you know what
the steps are, a production library reads as a set of decisions rather than
magic, and you will be able to tell when it is doing something you did not
expect.
