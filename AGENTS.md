# AGENTS.md

## Project Overview

Myo Mogille Bot is a Python Telegram group-chat bot that helps Russian-speaking
friends in Korea decide where to eat. A user starts a collection session with
`/eat` or a configured trigger phrase, group members send cravings, and a user
finishes with `/go` or the inline find button. The bot extracts food preferences,
searches Kakao Places near the configured area, ranks results, and replies with
Telegram HTML containing KakaoMap links.

The bot is intentionally small and runs by long polling from `bot.py`. Sessions are
in memory, so active sessions are lost when the process restarts.

There is no `CLAUDE.md` file in the current repository state.

## Tech Stack

- Language: Python 3
- Telegram framework: `python-telegram-bot`
- LLM provider: Gemini via `google-genai`
- Places provider: Kakao Local keyword search via `httpx`
- Configuration: environment variables loaded with `python-dotenv`
- Tests: `pytest` and `pytest-asyncio`
- Packaging/build system: unknown
- Linting/formatting tool: unknown
- Runtime deployment target: local long-polling process; no web server is present.

## Folder Structure

- `bot.py`: application entrypoint. Builds the Telegram app, wires dependencies into
  `application.bot_data`, registers handlers, starts polling, and closes resources
  on shutdown.
- `foodbot/config.py`: environment parsing and validation.
- `foodbot/handlers.py`: Telegram text, command, and callback handlers.
- `foodbot/session.py`: bounded in-memory per-chat sessions with lazy expiry.
- `foodbot/pipeline.py`: orchestration for LLM extraction, area resolution, Kakao
  search, ranking fallback, and formatting.
- `foodbot/llm.py`: Gemini wrapper and strict JSON parsing for craving extraction
  and place ranking.
- `foodbot/places.py`: Kakao client, `Place` model, response parsing, and merge
  logic.
- `foodbot/geo.py`: named-area resolution through Kakao.
- `foodbot/dictionary.py`: degraded Russian-to-Korean craving fallback.
- `foodbot/formatting.py`: Telegram HTML response formatting and escaping.
- `tests/`: async and unit tests for config, sessions, handlers, pipeline, LLM,
  Kakao parsing, formatting, and app cleanup.
- `.env.example`: documented environment template.
- `README.md`: user setup and command reference.
- `PROJECT_OVERVIEW.md`: architectural overview.
- `FIX_PLAN.md`: historical fix plan from hardening work.
- `AGENTS.md`: instructions for future coding agents working in this repository.

## Development Rules

- Do not read or print `.env`; it may contain real Telegram, Gemini, and Kakao keys.
- Do not run the real bot unless explicitly requested; it uses real Telegram,
  Gemini, and Kakao credentials from the environment.
- Keep provider calls behind `GeminiLLM` and `KakaoClient` so tests can use fakes.
- Keep Telegram handlers thin. Handler code should collect/validate Telegram state
  and delegate business behavior to `pipeline.run` or small helpers.
- Preserve graceful degradation:
  - LLM extraction failure should fall back to `dictionary.translate_cravings`.
  - LLM ranking failure should fall back to nearest places.
  - Kakao search failures with no usable results should return the temporary search
    error, not a false "nothing found" message.
- Preserve stale-button protection in `handlers.on_go`; callback message ids must
  match the active session prompt when available.
- Preserve session bounds (`MAX_SESSION_MESSAGES`, `MAX_SESSION_CHARS`) and the
  one-time group notice when new messages are ignored because the limit was reached.
- Always escape dynamic text sent with Telegram `ParseMode.HTML`.
- Close async provider resources through the app shutdown path.
- Do not introduce persistent storage unless explicitly requested.
- When adding configuration, update `Config`, `.env.example`, README configuration
  docs, and tests together.
- When changing pipeline behavior, add tests for LLM failure, Kakao failure, and
  no-result cases as applicable.

## Coding Style Rules

- Follow the existing compact module style: small dataclasses, direct functions,
  and explicit dependency objects.
- Use type hints for public helpers and dataclasses.
- Prefer explicit validation over permissive parsing for external data.
- Keep tests close to behavior and use fake clients instead of real network calls.
- Keep user-facing bot messages in Russian unless changing product language is part
  of the task.
- Use `from __future__ import annotations` in Python modules, matching the current
  codebase.
- Add comments only when they explain non-obvious behavior or fallback decisions.
- Avoid broad refactors when a small targeted change solves the issue.

## Commands

Create and activate a virtual environment on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

Install development/test dependencies. This also installs runtime dependencies
because `requirements-dev.txt` includes `-r requirements.txt`:

```powershell
pip install -r requirements-dev.txt
```

Create local configuration:

```powershell
copy .env.example .env
```

Then fill in the required keys in `.env`. Do not commit `.env`.

Run the bot locally:

```powershell
python bot.py
```

This requires valid Telegram, Gemini, Kakao, and default-location environment
configuration.

Run tests:

```powershell
python -m pytest -v
```

Build command:

```text
unknown
```

Dev server command:

```text
unknown
```

Lint command:

```text
unknown
```

Format command:

```text
unknown
```

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

Use `.env.example` as the template. Do not commit real `.env` files.

## Testing And Checking Instructions

- Run the full test suite after code changes:

```powershell
python -m pytest -v
```

- On this repository, using the existing virtual environment is usually:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

- Expected current coverage areas:
  - config parsing and validation;
  - session lifecycle, expiry, and bounds;
  - Telegram handler session flow and callback safety;
  - LLM JSON parsing and ranking filters;
  - Kakao parsing and place merging;
  - pipeline fallbacks and provider failure handling;
  - Telegram HTML formatting and escaping;
  - app resource cleanup.
- Do not add tests that require live Telegram, Gemini, or Kakao credentials. Use fake
  clients or `httpx.MockTransport`.
- Prefer `load_config(dict(...))` in config-dependent tests instead of mutating real
  environment variables.
- If pytest warns that it cannot write `.pytest_cache`, treat it as a cache
  permission issue unless tests fail.

## Safe Workflow For Future Changes

1. Check status first:

```powershell
git status --short --branch
```

2. Read the relevant module and matching tests before editing.
3. Add or update tests for behavior changes, especially around provider failures,
   callback handling, session limits, and HTML output.
4. Make the smallest scoped code change that satisfies the tests.
5. Run targeted tests first when useful, then the full suite:

```powershell
python -m pytest -v
```

6. Review the diff before committing:

```powershell
git diff --stat
git diff
```

7. Keep secrets out of logs, commits, and test fixtures.
8. Do not rewrite Git history or force-push unless explicitly requested.
9. Do not change user-facing Russian messages casually; update tests and docs when
   message behavior changes.
10. Update `README.md`, `.env.example`, and `PROJECT_OVERVIEW.md` when configuration,
    setup steps, or architecture change.
11. Keep commits scoped. If a change touches Telegram handlers, pipeline behavior,
    and docs, make sure each part is covered by tests or a clear manual check.
