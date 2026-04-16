# How OAuth 2.0 Works: Visual Guide

> A picture is worth a thousand RFCs.

---

## The Big Picture

```
 YOU                YOUR APP               GITHUB              GITHUB API
  │                    │                      │                     │
  │  Click "Login"     │                      │                     │
  │ ──────────────►    │                      │                     │
  │                    │                      │                     │
  │    Redirect to GitHub                     │                     │
  │ ◄──────────────    │                      │                     │
  │                    │                      │                     │
  │  "Authorize this app?"                    │                     │
  │ ──────────────────────────────────────►   │                     │
  │                    │                      │                     │
  │  Click "Yes"       │                      │                     │
  │ ──────────────────────────────────────►   │                     │
  │                    │                      │                     │
  │    Redirect back with code                │                     │
  │ ◄──────────────────────────────────────   │                     │
  │ ──────────────►    │                      │                     │
  │                    │                      │                     │
  │                    │  POST: code→token    │                     │
  │                    │ ────────────────►    │                     │
  │                    │                      │                     │
  │                    │  access_token        │                     │
  │                    │ ◄────────────────    │                     │
  │                    │                      │                     │
  │                    │  GET /user (token)                         │
  │                    │ ─────────────────────────────────────►     │
  │                    │                                            │
  │                    │  {name, email, avatar}                     │
  │                    │ ◄─────────────────────────────────────     │
  │                    │                      │                     │
  │  "Welcome, Alice!" │                      │                     │
  │ ◄──────────────    │                      │                     │
  │                    │                      │                     │
```

---

## What Travels Where

Understanding what goes through the browser vs. server-to-server
is the key to understanding OAuth security.

```
┌─────────────────────────────────────────────────────┐
│                BROWSER (visible)                     │
│                                                      │
│  → Authorization URL (client_id, scopes, state)      │
│  ← Authorization code (in redirect URL)              │
│  ← Session cookie (after login complete)             │
│                                                      │
│  The authorization CODE travels here.                │
│  That's why it's short-lived and one-time-use.       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│             SERVER-TO-SERVER (hidden)                 │
│                                                      │
│  → Code + client_secret → token endpoint             │
│  ← Access token (from provider)                      │
│  → Access token → API endpoint                       │
│  ← User data (from provider)                         │
│                                                      │
│  The access TOKEN only travels here.                 │
│  The user's browser never sees it.                   │
└─────────────────────────────────────────────────────┘
```

---

## The Token Lifecycle

```
 Authorization Code          Access Token              API Access
┌───────────────────┐    ┌────────────────────┐    ┌──────────────┐
│ Lives: ~10 min    │    │ Lives: ~1 hour     │    │ Until token  │
│ Use: exactly once │───►│ Use: many times    │───►│ expires      │
│ Where: URL param  │    │ Where: server only │    │              │
│ Risk: low         │    │ Risk: medium       │    │              │
└───────────────────┘    └────────────────────┘    └──────────────┘
                                │
                                │ expired?
                                ▼
                         ┌────────────────────┐
                         │ Refresh Token      │
                         │ Lives: days/months │
                         │ Gets new access    │
                         │ token silently     │
                         └────────────────────┘
```

---

## OAuth vs. Giving Away Your Password

```
WITHOUT OAUTH                        WITH OAUTH
─────────────                        ──────────

User: "Here's my password"           User: "I authorize read:user scope"
  │                                    │
  ▼                                    ▼
App stores password                   App gets a token
  │                                    │
  ▼                                    ▼
App can do ANYTHING                   App can ONLY read profile
  │                                    │
  ▼                                    ▼
To revoke: change password            To revoke: click a button
(breaks everything)                   (only affects this app)
  │                                    │
  ▼                                    ▼
App hacked = password leaked          App hacked = token expires
(game over)                           (limited damage)
```

---

## The State Parameter (CSRF Attack Prevention)

```
WITHOUT STATE:                       WITH STATE:
─────────────                        ───────────

Attacker starts OAuth flow            Attacker starts OAuth flow
Gets authorization code               Gets authorization code
  │                                      │
  ▼                                      ▼
Tricks victim's browser into          Tricks victim's browser into
  sending code to YOUR app              sending code to YOUR app
  │                                      │
  ▼                                      ▼
Your app accepts it!                  Your app checks: does the state
Attacker's GitHub account               match what I stored? NO!
  is now linked to victim's           Request rejected. Attack failed.
  session on your app.
```

---

*These diagrams are available as Mermaid source in `docs/diagrams/flow.mmd`
if you want to edit or extend them.*
