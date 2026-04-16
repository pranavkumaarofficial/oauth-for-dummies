# Contributing to OAuth for Dummies

Thanks for wanting to contribute. This project is built for beginners, so keeping things simple and clear matters more than being clever.

## Ways to Contribute

### Add a New OAuth Provider

This is the most useful contribution you can make. Each new provider helps someone.

How to do it:

1. Create a new file in `providers/` (copy `github.py` as a starting point)
2. Subclass `OAuthProvider` and fill in the 5 required fields
3. Implement `normalize_userinfo()` to map the provider's response
4. Add the provider config to `providers/registry.py`
5. Update `.env.example` with the new keys
6. Test it and submit a PR

Providers we'd like to see:
- Discord
- Spotify
- Twitter/X
- LinkedIn
- Twitch
- Facebook
- Apple
- Microsoft

### Improve Documentation
- Fix typos or unclear explanations
- Add diagrams
- Translate the tutorial into other languages

### Improve the Demo UI
- Mobile responsiveness
- Accessibility improvements
- Dark/light mode toggle

### Add Tests
- Unit tests for providers
- Integration tests for the auth flow
- Edge case coverage

### Report Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## Development Setup

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/oauth-for-dummies.git
cd oauth-for-dummies

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your OAuth keys

uvicorn app.main:app --reload

# Run tests
pytest
```

## Code Style

Keep it beginner-friendly:

- Clear variable names over clever abbreviations
- Comments that explain why, not just what
- Simple patterns over advanced abstractions
- Short files. If a file is over 150 lines, consider splitting it

We use standard Python formatting. If you have `black` installed, run it:

```bash
black .
```

## Submitting a Pull Request

1. Fork the repository
2. Create a branch: `git checkout -b add-discord-provider`
3. Make your changes and commit with a clear message
4. Push to your fork: `git push origin add-discord-provider`
5. Open a PR with a description of what you changed and why

## Questions?

Open an issue or reach out at kumaarp.in@gmail.com. No question is too basic.
