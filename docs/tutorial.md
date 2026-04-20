# OAuth 2.0 Tutorial — From Zero to "I Get It"

> This tutorial assumes you know basic Python and have used `pip install`.
> That's it. No prior auth knowledge needed.

---

## Chapter 1: Why Does OAuth Exist?

Imagine you're building an app that shows someone's GitHub repositories.
The old way: ask for their GitHub username and password. **Terrible idea.**

- You're storing someone else's password
- If your app gets hacked, their GitHub is compromised
- They can't limit what you access
- They can't revoke your access without changing their password

**OAuth fixes all of this.** The user tells GitHub: *"Let this app see my repos."*
Your app gets a token — a temporary key that only works for what the user allowed.

---

## Chapter 2: The Four Characters

Every OAuth flow has four players:

| Who | What They Do | In Our App |
|-----|-------------|------------|
| **Resource Owner** | The user who owns the data | You, the human |
| **Client** | The app that wants access | Our FastAPI app |
| **Authorization Server** | Verifies the user and issues tokens | GitHub's OAuth server |
| **Resource Server** | Holds the protected data | GitHub's API |

Sometimes the Authorization Server and Resource Server are the same company
(like GitHub). The point is they're conceptually separate roles.

---

## Chapter 3: The Flow (Plain English)

Here's the entire OAuth 2.0 Authorization Code flow in plain language:

**Step 1 — Your app says "go ask GitHub"**

Your app builds a URL to GitHub's authorization page and redirects the user there.
The URL includes your app's ID and what permissions you want.

```
https://github.com/login/oauth/authorize?
  client_id=abc123&
  redirect_uri=http://localhost:8000/auth/github/callback&
  scope=read:user&
  state=random-csrf-token
```

**Step 2 — The user says "yes, I trust this app"**

GitHub shows a consent screen: *"OAuth for Dummies wants to access your profile."*
The user clicks "Authorize."

**Step 3 — GitHub sends a code to your app**

GitHub redirects the user back to your app with a short-lived authorization code:

```
http://localhost:8000/auth/github/callback?code=xyz789&state=random-csrf-token
```

This code is NOT the access token. It's a one-time-use ticket that expires in minutes.

**Step 4 — Your app trades the code for a token**

Your app makes a server-to-server POST request (the user doesn't see this):

```
POST https://github.com/login/oauth/access_token
  client_id=abc123
  client_secret=super_secret
  code=xyz789
```

GitHub responds with an access token.

**Step 5 — Your app uses the token**

Now your app can call GitHub's API:

```
GET https://api.github.com/user
Authorization: Bearer ghp_abc123token
```

And GitHub responds with the user's profile data. Done.

---

## Chapter 4: Why Not Just Send the Token Directly?

Good question. Why the extra step with the "code"?

Because the authorization code travels through the user's browser (in the URL).
If someone intercepts it, they still can't use it without your `client_secret`,
which never leaves your server.

The access token, on the other hand, only travels server-to-server — it never
touches the browser. This is called the **Authorization Code Grant** and it's
the most secure standard OAuth flow.

---

## Chapter 5: The State Parameter (CSRF Protection)

Notice the `state` parameter in Step 1? Here's why it matters.

Without it, an attacker could:
1. Start an OAuth flow with YOUR app
2. Get the authorization code
3. Trick another user's browser into sending that code to your callback

With the `state` parameter, your app generates a random token, stores it,
and checks that it matches when the callback comes in. If it doesn't match,
someone is trying something sketchy.

**In our code** (`app/auth/routes.py`):
```python
# On login — generate and save state
auth_url, state = provider.get_authorization_url()
store.save_state(state, provider_name)

# On callback — verify state
saved_provider = store.verify_state(state)
if saved_provider is None:
    # CSRF attack! Reject this request.
    raise HTTPException(400, "Invalid state parameter")
```

---

## Chapter 6: Understanding Scopes

Scopes are how you ask for specific permissions. Instead of getting full access
to someone's account, you only request what you need.

| Scope | What It Gives You |
|-------|-------------------|
| `read:user` | Basic profile info (name, avatar) |
| `user:email` | Email address |
| `repo` | Full access to repositories |
| `read:org` | Read organization membership |

**Golden rule:** request the minimum scopes you need. Users trust apps that
ask for less.

In our code, each provider defines its default scopes:
```python
class GitHubProvider(OAuthProvider):
    default_scopes = ["read:user", "user:email"]
```

---

## Chapter 7: What About Refresh Tokens?

Access tokens expire. When they do, your app has two options:

1. **Make the user login again** — simple but annoying
2. **Use a refresh token** — seamless but more complex

A refresh token is a long-lived token that can request new access tokens
without user interaction. Not all providers give you one (GitHub doesn't
by default, but Google does).

The flow looks like:
```
POST /oauth/token
  grant_type=refresh_token
  refresh_token=your_refresh_token
  client_id=abc123
  client_secret=super_secret
```

We don't implement refresh tokens in the basic demo to keep things simple,
but check the `providers/base.py` — the `OAuthToken` dataclass already
has a `refresh_token` field ready for when you want to add it.

---

## Chapter 8: Running the Demo

Now that you understand the theory, go see it in action:

```bash
# 1. Set up GitHub OAuth keys (see README.md)
# 2. Start the app
uvicorn app.main:app --reload

# 3. Open http://localhost:8000
# 4. Click "Login with GitHub"
# 5. Watch your terminal — every step is logged
```

Your terminal will show something like:

```
============================================================
  🔗 STEP 1 — Redirect user to GitHub
============================================================
  URL: https://github.com/login/oauth/authorize
  client_id:    abc12345...
  redirect_uri: http://localhost:8000/auth/github/callback
  scope:        read:user user:email
  state:        kF9x2mQp...
============================================================
```

Follow along as each step happens in real time.

---

## Chapter 9: Common Mistakes

**"Redirect URI mismatch"**
The callback URL in your code must EXACTLY match what you registered
with the provider. Even a trailing slash difference will fail.

**"Invalid client_id"**
Double-check your `.env` file. Make sure there are no extra spaces
or quotes around the values.

**"Bad verification code"**
Authorization codes are one-time-use and expire quickly. If you
refresh the callback page, the code is already spent. Start the
flow over.

**"Scope not authorized"**
You're requesting a scope that your OAuth app isn't approved for.
Check your app settings on the provider's developer portal.

---

## Chapter 10: What Next?

Now that you understand OAuth 2.0, here are your next steps:

1. **Add another provider** — try Google or Discord to see how the
   pattern stays the same across providers
2. **Read about PKCE** — an extra security layer for mobile/SPA apps
3. **Look at Authlib** — now that you understand the concepts, a
   production library will make much more sense
4. **Build something real** — add OAuth login to your own project

---

*If this tutorial helped you, give the repo a ⭐ on GitHub.
It helps other confused developers find it.*
