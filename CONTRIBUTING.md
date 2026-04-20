# Contributing to OAuth for Dummies

First off — **thank you!** This project exists to help beginners understand OAuth, and every contribution makes it better for the next person who's confused.

## 🎯 Ways to Contribute

### 🌐 Add a New OAuth Provider
This is the **#1 most impactful contribution** you can make. Every new provider helps someone.

**How to do it:**

1. Create a new file in `providers/` (copy `github.py` as a starting point)
2. Subclass `OAuthProvider` and fill in the 5 required fields
3. Implement `normalize_userinfo()` to map the provider's response
4. Add the provider config to `providers/registry.py`
5. Update `.env.example` with the new keys
6. Test it and submit a PR

**Providers we'd love to see:**
- 🟣 Discord
- 🟢 Spotify
- 🐦 Twitter/X
- 🔗 LinkedIn
- 🎮 Twitch
- 📘 Facebook
- 🍎 Apple
- 🏢 Microsoft

### 📝 Improve Documentation
- Fix typos or unclear explanations
- Add diagrams or illustrations
- Translate the tutorial into other languages
- Write a blog post about the project

### 🎨 Improve the Demo UI
- Make it responsive on mobile
- Add animations to the flow steps
- Improve accessibility
- Dark/light mode toggle

### 🧪 Add Tests
- Unit tests for providers
- Integration tests for the auth flow
- Edge case coverage

### 🐛 Report Bugs
Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## 🔧 Development Setup

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/pranavkumaarofficial/oauth-for-dummies.git
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

## 📐 Code Style

Keep it **beginner-friendly**. That means:

- **Clear variable names** over clever abbreviations
- **Comments that explain WHY**, not just what
- **Simple patterns** over advanced abstractions
- **Short files** — if a file is over 150 lines, consider splitting it

We use standard Python formatting. If you have `black` installed, run it:

```bash
black .
```

## 🚀 Submitting a Pull Request

1. **Fork** the repository
2. **Create a branch**: `git checkout -b add-discord-provider`
3. **Make your changes** and commit with a clear message
4. **Push** to your fork: `git push origin add-discord-provider`
5. **Open a PR** with a description of what you changed and why

## 💬 Questions?

Open an issue with the "question" label. No question is too basic — this project is literally called "for Dummies."

---

**Every contribution counts.** Whether it's fixing a typo or adding a whole new provider, you're helping someone learn. Thank you. 🙏
