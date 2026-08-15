# How OAuth 2.0 works, visually

Diagrams for the parts of OAuth that are hard to hold in your head. If you would
rather watch it happen with real requests, run the app and open Learn Mode.

---

## The whole flow

```
 YOU                YOUR APP               GITHUB              GITHUB API
  |                    |                      |                     |
  |  Click "Login"     |                      |                     |
  | ---------------->  |                      |                     |
  |                    |                      |                     |
  |    Redirect to GitHub                     |                     |
  | <----------------  |                      |                     |
  |                    |                      |                     |
  |  "Authorize this app?"                    |                     |
  | -------------------------------------->   |                     |
  |                    |                      |                     |
  |  Click "Yes"       |                      |                     |
  | -------------------------------------->   |                     |
  |                    |                      |                     |
  |    Redirect back with code                |                     |
  | <--------------------------------------   |                     |
  | ---------------->  |                      |                     |
  |                    |                      |                     |
  |                    |  POST: code to token |                     |
  |                    | ---------------->    |                     |
  |                    |                      |                     |
  |                    |  access_token        |                     |
  |                    | <----------------    |                     |
  |                    |                      |                     |
  |                    |  GET /user (token)                         |
  |                    | ------------------------------------->     |
  |                    |                                            |
  |                    |  {name, email, avatar}                     |
  |                    | <-------------------------------------     |
  |                    |                      |                     |
  |  "Welcome, Alice"  |                      |                     |
  | <----------------  |                      |                     |
  |                    |                      |                     |
```

---

## What travels where

This is the idea the rest of OAuth security rests on. Some parts of the flow go
through the user's browser, where they are visible in the address bar and in
devtools. Other parts go directly between your server and the provider, where
the user never sees them.

```
+-----------------------------------------------------+
|                 BROWSER (visible)                   |
|                                                     |
|  ->  Authorization URL (client_id, scopes, state)   |
|  <-  Authorization code, in the redirect URL        |
|  <-  Session cookie, once login completes           |
|                                                     |
|  The authorization CODE travels here, which is why  |
|  it is short-lived and can only be used once.       |
+-----------------------------------------------------+

+-----------------------------------------------------+
|              SERVER TO SERVER (hidden)              |
|                                                     |
|  ->  Code plus client_secret, to the token endpoint |
|  <-  Access token                                   |
|  ->  Access token, to the API                       |
|  <-  User data                                      |
|                                                     |
|  The access TOKEN only travels here. The user's     |
|  browser never sees it, and neither does anyone     |
|  watching the address bar.                          |
+-----------------------------------------------------+
```

Once you have this straight, a lot of OAuth stops being arbitrary. The code is
public because it has to cross the browser, so it is made useless on its own.
The secret never crosses the browser, so it can stay secret. The token is the
valuable thing, so it stays on the hidden side.

---

## How long each thing lives

```
 Authorization Code          Access Token              API access
+-------------------+    +--------------------+    +--------------+
| Lives: ~10 min    |    | Lives: ~1 hour     |    | Until the    |
| Use: exactly once |--->| Use: many times    |--->| token        |
| Where: URL param  |    | Where: server only |    | expires      |
| Risk if leaked:   |    | Risk if leaked:    |    |              |
|   low             |    |   high             |    |              |
+-------------------+    +--------------------+    +--------------+
                                  |
                                  | expired?
                                  v
                         +--------------------+
                         | Refresh token      |
                         | Lives: days to     |
                         |   months           |
                         | Gets a new access  |
                         |   token quietly    |
                         +--------------------+
```

---

## Why not just hand over the password

```
WITHOUT OAUTH                        WITH OAUTH
-------------                        ----------

You give the app your password       You approve the read:user scope
  |                                    |
  v                                    v
The app stores your password         The app gets a token
  |                                    |
  v                                    v
It can do anything you can do        It can only read your profile
  |                                    |
  v                                    v
To revoke, change your password      To revoke, click one button
  (which breaks every other app)       (which affects only this app)
  |                                    |
  v                                    v
App gets breached, your password     App gets breached, a limited
  is out                               token expires
```

---

## The state parameter, and the part people get wrong

The `state` parameter exists to stop login CSRF, where an attacker makes your
browser complete *their* login, leaving you signed into *their* account on a site
you trust. Anything you then upload, write or connect goes into their account.

Most tutorials describe the check as "store the state, then compare it on the way
back". That is not sufficient, and the gap is easy to miss.

```
THE INSUFFICIENT CHECK               THE CHECK THAT WORKS
----------------------               --------------------

App stores issued states             App stores issued states AND
in a set on the server                 sets the state in a cookie
  |                                    |
  v                                    v
Attacker starts a login,             Attacker starts a login,
gets a real code and state             gets a real code and state
  |                                    |
  v                                    v
Attacker sends you the               Attacker sends you the
callback URL                           callback URL
  |                                    |
  v                                    v
Your browser opens it. The           Your browser opens it. The state
state IS in the server's set,          is in the server's set, but your
so the check passes.                   browser has no matching cookie.
  |                                    |
  v                                    v
You are now signed in as             Rejected. The flow was never
the attacker.                          started in this browser.
```

The rule: the state has to prove that *this browser* started the flow, not merely
that the server issued the value to somebody. Binding it to a cookie is the
simplest way to do that.

This project shipped the insufficient version at first. The fix is in
`oauth_for_dummies/scaffold/oauth_routes.py`, and there is a test asserting that
a state issued to one browser cannot be redeemed by another.

---

The Mermaid source for these diagrams is in `docs/diagrams/flow.mmd` if you want
to edit or extend them.
