# AGENTS.md

Instructions for coding agents working in this repository.

## Project State

Myo Mogille Bot is a compact Python Telegram group-chat bot for helping
Russian-speaking groups in Korea decide where to eat. The bot runs locally with
Telegram long polling from `bot.py`; it is online only while that process is
running.

The runtime flow is:

1. A user starts a collection session with `/eat` or a configured trigger phrase.
2. Group members send food or drink cravings.
3. A user finishes with `/go` or the inline find button.
4. The bot extracts food intent, expands Korean search terms, searches Kakao
   Places near the configured area, optionally checks Naver Blog Search snippets,
   ranks candidates, and returns Telegram HTML with KakaoMap links.

Sessions are in memory only. Restarting the process loses active sessions.

## Project Stack

- Language: Python 3.
- Telegram framework: `python-telegram-bot`.
- LLM provider: Gemini via `google-genai`.
- Places provider: Kakao Local keyword search via `httpx`.
- Optional evidence provider: Naver Search API via `httpx`.
- Configuration: `.env` and process environment through `python-dotenv`.
- Tests: `pytest` and `pytest-asyncio`.
- Build system: none currently.
- Lint and format tooling: none currently.
- Package manager scripts: none. There is no `package.json`.

## Repository Layout

- `bot.py`: application entrypoint, dependency wiring, handler registration, long
  polling startup, and async resource shutdown.
- `foodbot/config.py`: environment parsing, validation, defaults, and `Config`.
- `foodbot/handlers.py`: Telegram command, text, and callback handlers.
- `foodbot/session.py`: bounded in-memory per-chat sessions with timeout expiry.
- `foodbot/pipeline.py`: extraction, area resolution, search, evidence, ranking,
  and formatting orchestration.
- `foodbot/llm.py`: Gemini wrapper and strict JSON parsing.
- `foodbot/places.py`: Kakao client, `Place` model, response parsing, and merge
  logic.
- `foodbot/naver.py`: Naver Search API client and response parsing.
- `foodbot/evidence.py`: blog snippet evidence extraction.
- `foodbot/search_queries.py`: Korean query expansion rules.
- `foodbot/geo.py`: named-area resolution through Kakao.
- `foodbot/dictionary.py`: fallback Russian-to-Korean craving dictionary.
- `foodbot/formatting.py`: Telegram HTML response formatting and escaping.
- `tests/`: unit and async tests for config, handlers, sessions, providers,
  pipeline behavior, fallbacks, and formatting.
- `README.md`: user setup and command reference.
- `PROJECT_OVERVIEW.md`: architecture and behavior notes.
- `.env.example`: local configuration template.

## Key Commands

Create and activate a virtual environment on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

Install development and test dependencies:

```powershell
pip install -r requirements-dev.txt
```

Create local configuration:

```powershell
copy .env.example .env
```

Fill in real secrets in `.env`. Never commit `.env`.

Run the bot locally:

```powershell
python bot.py
```

Run the full test suite:

```powershell
python -m pytest -v
```

Run tests with the checked-in virtual environment if it exists:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

There is no build command, dev server command, lint command, or format command in
the current project state.

## Configuration

Required environment variables:

- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY`
- `KAKAO_REST_API_KEY`
- `DEFAULT_LAT`
- `DEFAULT_LNG`
- `DEFAULT_AREA_NAME`

Optional environment variables:

- `SEARCH_RADIUS_M`, default `1500`
- `RESULTS_COUNT`, default `3`
- `SESSION_TIMEOUT_MIN`, default `20`
- `LLM_MODEL`, default `gemini-2.5-flash`
- `TRIGGER_PHRASES`, comma-separated trigger override
- `MAX_SESSION_MESSAGES`, default `50`
- `MAX_SESSION_CHARS`, default `4000`
- `NAVER_CLIENT_ID`, optional
- `NAVER_CLIENT_SECRET`, optional
- `NAVER_BLOG_EVIDENCE_ENABLED`, default `false`
- `NAVER_BLOG_EVIDENCE_LIMIT`, default `3`

Use `.env.example` as the source of truth for local setup. Do not print or read
real `.env` contents unless the user explicitly asks and understands the secret
risk.

## Code Rules

- Keep changes small and aligned with the existing module boundaries.
- Preserve `from __future__ import annotations` in Python modules.
- Use type hints for public helpers, dataclasses, and provider-facing models.
- Keep Telegram handlers thin. Handler code should validate Telegram state and
  delegate business logic to `pipeline.run` or small helpers.
- Keep external services behind dependency objects (`GeminiLLM`, `KakaoClient`,
  `NaverClient`) so tests can use fakes.
- Do not add live network calls to tests. Use fake clients, simple stubs, or
  `httpx.MockTransport`.
- Always escape dynamic text sent with Telegram `ParseMode.HTML`.
- Keep user-facing bot messages in Russian unless the task explicitly changes the
  product language.
- Preserve graceful degradation:
  - Gemini extraction failure falls back to `dictionary.translate_cravings`.
  - Gemini ranking failure falls back to deterministic scored order.
  - Kakao provider failures produce a temporary search error instead of a false
    no-results message.
  - Optional Naver evidence must not be required for normal recommendations.
- Preserve stale inline-button protection in `handlers.on_go`.
- Preserve session bounds and the one-time group notice when input limits are
  reached.
- Close async provider resources through the application shutdown path.
- Do not introduce persistent storage, deployment tooling, or new provider
  abstractions unless the task requires it.
- When adding or changing configuration, update `Config`, `.env.example`, README
  configuration docs, project overview docs, and tests together.

## Testing Guidance

Run targeted tests first when changing a narrow behavior, then run the full suite:

```powershell
python -m pytest -v
```

Important coverage areas in this repo:

- Config defaults, overrides, validation errors, and optional Naver settings.
- Session lifecycle, expiry, bounds, and trigger matching.
- Telegram handler flow for `/eat`, `/go`, collection messages, callback cleanup,
  stale buttons, and HTML parse mode.
- LLM JSON parsing and fallback behavior.
- Kakao response parsing, provider errors, place merging, and no-result handling.
- Naver response parsing and blog evidence extraction.
- Pipeline happy path, no-preference nudges, no-result responses, dictionary
  fallback, blog-evidence fallback, and ranking fallback.
- Telegram HTML escaping and output formatting.
- Application resource cleanup.

## ExecPlans

When writing complex features or significant refactors, use an ExecPlan as
described in `.agent/PLANS.md` from design through implementation.

## Self-Review Checklist

Before finishing a change:

1. Check the working tree with `git status --short`.
2. Review the diff with `git diff --stat` and `git diff`.
3. Confirm no secrets from `.env` or API responses were added to code, docs, test
   fixtures, or logs.
4. Confirm changed behavior has tests, especially around provider failures,
   callback handling, session limits, config validation, and HTML output.
5. Confirm all affected docs are updated when commands, setup, config, or
   architecture changed.
6. Run `python -m pytest -v` when dependencies are installed.
7. If tests cannot be run, state exactly why and note the residual risk.

Keep commits scoped and avoid unrelated refactors.
