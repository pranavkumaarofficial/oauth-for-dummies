# Contributing

Thanks for considering it. This project exists to make OAuth understandable, so
the most valuable contributions are usually the ones that make something clearer,
not just the ones that add features.

## Getting set up

```bash
git clone https://github.com/YOUR-USERNAME/oauthlens.git
cd oauthlens

python -m venv venv
source venv/bin/activate      # venv\Scripts\activate on Windows

pip install -e .
uvicorn app.main:app --reload
```

Open http://localhost:8000 and use the Demo Provider. You do not need any
credentials to work on most of this: the demo provider is a real OAuth server
running inside the app.

Copy `.env.example` to `.env` only when you want to test against a real provider.

Running the tests:

```bash
pytest -q
```

## Good things to pick up

**Add a provider.** Currently GitHub, Google, Discord, Spotify, Microsoft and
LinkedIn. Twitch, Apple, GitLab and Facebook would all be welcome.

1. Copy `providers/github.py` as a starting point
2. Subclass `OAuthProvider`, fill in the URLs and scopes
3. Implement `normalize_userinfo()` to map their response to ours
4. Fill in `setup_url`, `setup_steps` and `gotcha`. The Settings page renders
   these, so the provider carries its own instructions
5. Register it in `providers/registry.py` and add the keys to `.env.example`

The `gotcha` field is worth real effort. It should be the specific thing that
wastes an hour, not general advice. Look at the existing ones for the tone.

**Host the demo.** The single most useful thing anyone could do right now. The
demo provider works with no credentials, so the app can be deployed as a live
demo that people try without cloning.

**Flask support in the scaffolder.** The CLI writes FastAPI code today.

**Token refresh.** `OAuthToken` already has the field. Nothing uses it yet.

**Documentation.** If something confused you, that is a bug worth reporting even
if the code is correct.

## Reporting a bug

Include what you expected, what happened, how to reproduce it, and your Python
version and OS.

Security issues are the exception: please open a private security advisory on
GitHub rather than a public issue.

## Code style

The whole project is meant to be read by someone learning OAuth, so readability
beats cleverness every time.

- Clear names over short ones
- Comments that explain why, not what
- Plain patterns over abstractions
- No em dashes in code, comments or docs. Commas, colons and full stops instead
- No emoji

If a comment is explaining a security decision, say what breaks without it.
Those comments are doing the teaching.

We use standard formatting. `black .` if you have it.

## Tests

New behaviour needs a test. Security fixes especially: write the test so that it
fails against the old code, then confirm that it does. A regression test that
passes either way is worse than none, because it looks like protection.

`tests/test_scaffold_routes.py` covers the code that ships to users through
`oauthlens`. That is the part most worth protecting.

## Pull requests

1. Branch: `git checkout -b add-twitch-provider`
2. Commit with a message explaining why, not just what
3. Push and open a PR describing the change and how you verified it

Questions are welcome as issues.
