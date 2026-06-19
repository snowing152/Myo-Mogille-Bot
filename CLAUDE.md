# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Telegram group-chat bot ("куда пойдём 🍽"). When someone sends a trigger phrase (e.g.
«куда пойдём кушать?») or `/eat`, the bot collects everyone's food/drink cravings from the
chat, then replies with ~3 nearby Korean restaurants (via Kakao Maps) ranked by an LLM
(Gemini), with KakaoMap links. Runs via long-polling on `python-telegram-bot`.

## Commands

```powershell
# setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, KAKAO_REST_API_KEY, DEFAULT_LAT/LNG/AREA_NAME

# run the bot
python bot.py

# dev / tests
pip install -r requirements-dev.txt
python -m pytest -v
python -m pytest tests/test_pipeline.py -v          # single file
python -m pytest tests/test_pipeline.py::test_name  # single test
```

There is no lint/typecheck command configured in this repo.

## Architecture

Flow: `bot.py` wires Telegram handlers → `foodbot/handlers.py` manages session
collection → `foodbot/pipeline.py` orchestrates the actual craving → search → rank →
format pipeline.

- **`bot.py`** — builds the `Application`, stashes shared singletons (`config`, `sessions`,
  `kakao`, `llm`, `default_point`) in `app.bot_data`, registers handlers, runs polling.
- **`foodbot/session.py`** — `SessionStore`: in-memory per-`chat_id` collection sessions
  with lazy expiry (`SESSION_TIMEOUT_MIN`). `is_trigger()` matches trigger phrases against
  incoming text. No persistence — state is lost on restart.
- **`foodbot/handlers.py`** — Telegram entry points (`on_text`, `on_eat`, `on_go`). `on_text`
  starts a session on a trigger phrase or appends to an active session's messages. `on_go`
  (command `/go` or the "🍽 Найти места" inline button) snapshots the session's messages,
  ends the session, and calls `pipeline.run`.
- **`foodbot/pipeline.py`** — the core orchestration, with **degraded-mode fallbacks at every
  LLM/network step** so the bot still responds if Gemini or Kakao is down:
  1. Extract cravings + area via `llm.extract_cravings()`; on failure, fall back to
     `dictionary.translate_cravings()` (static RU→KR keyword map).
  2. Resolve search center via `geo.resolve_area()` (geocodes the named area through Kakao);
     falls back to `default_point` from config.
  3. Search Kakao for each query (`places.merge_places` dedupes/sorts by distance); if empty,
     retry once with doubled radius.
  4. Rank results via `llm.rank_places()`; on failure, fall back to first-N nearest results.
  5. Format the final reply via `formatting.build_message()`.
- **`foodbot/llm.py`** — `GeminiLLM` is the only LLM provider implementation; its docstring
  notes it's a "provider-agnostic surface" meant to be swapped out by replacing the class.
  Prompts force strict JSON responses (`parse_extract`/`parse_ranking` parse and validate them,
  stripping markdown code fences if present).
- **`foodbot/places.py`** — `KakaoClient` wraps the Kakao keyword-search REST API
  (`search` for places near a point, `geocode` for resolving an area name to coordinates).
- **`foodbot/config.py`** — `load_config()` reads `.env`/env vars into a frozen `Config`
  dataclass; raises `ConfigError` if a required key is missing. Accepts an explicit `env` dict
  (used in tests) to bypass `.env`/`os.environ`.

## Notes

- All bot-facing strings (prompts, errors, LLM system prompts) are in Russian; LLM search
  queries/output are in Korean.
- Tests live in `tests/`, mirroring each `foodbot/` module 1:1; `pytest-asyncio` is in
  `auto` mode (see `pytest.ini`), so async test functions don't need explicit markers.