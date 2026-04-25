# Contributing to OAuth for Dummies

Thank you for considering a contribution. This project helps developers add OAuth to FastAPI apps quickly, and every improvement makes it better for the next person.

## Ways to contribute

### Add a new OAuth provider

This is the most impactful contribution you can make. The project currently supports GitHub, Google, Discord, Spotify, Microsoft, and LinkedIn. Providers we'd like to add:

- Twitter/X
- Apple
- Facebook
- Twitch

How to do it:

1. Create a new file in `providers/` (copy `github.py` as a starting point)
2. Subclass `OAuthProvider` and fill in the 5 required fields
3. Implement `normalize_userinfo()` to map the provider's response
4. Add the provider config to `providers/registry.py`
5. Update `.env.example` with the new keys
6. Test it and submit a PR

### Improve the CLI

- Add `--framework flask` support (currently FastAPI only)
- Interactive mode for the scaffold
- Better error messages for missing credentials

### Add tests

- Unit tests for individual providers
- Integration tests for the auth flow
- Tests for the scaffold files

### Improve documentation

- Fix typos or unclear explanations
- Add diagrams or illustrations
- Write a blog post about the project

### Report bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## Development setup

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR-USERNAME/oauth-for-dummies.git
cd oauth-for-dummies

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your OAuth keys

# Run the app
uvicorn app.main:app --reload

# Run tests
pytest
```

## Code style

Keep it readable. That means:

- Clear variable names over clever abbreviations
- Comments that explain why, not just what
- Simple patterns over advanced abstractions
- Short files -- if a file is over 150 lines, consider splitting it

We use standard Python formatting. If you have `black` installed:

```bash
black .
```

## Submitting a pull request

1. Fork the repository
2. Create a branch: `git checkout -b add-twitter-provider`
3. Make your changes and commit with a clear message
4. Push to your fork: `git push origin add-twitter-provider`
5. Open a PR with a description of what you changed and why

## Questions?

Open an issue with the "question" label.
