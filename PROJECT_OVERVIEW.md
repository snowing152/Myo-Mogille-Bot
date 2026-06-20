# Project Overview

## Purpose

This project is a Telegram group-chat bot for helping friends decide where to eat.
When someone starts a food-planning session with `/eat` or a trigger phrase such as
"куда пойдем кушать?", the bot collects group messages. A user then sends `/go` or
taps the inline button, and the bot extracts food and drink preferences, searches
nearby Korean restaurants, and replies with a short list of recommended places.

The current product focus is Russian-language chat input for groups in Korea. Search
queries are converted to Korean terms before calling Kakao Places.

## Main Capabilities

- Starts a per-chat collection session from `/eat` or configured trigger phrases.
- Collects free-text cravings from group members during the active session.
- Lets anyone finish the session with `/go` or the inline find-places button.
- Uses Gemini to extract cravings, Korean search queries, and an optional area.
- Uses Kakao local keyword search to find restaurants near the default or resolved
  area.
- Uses Gemini to rank results, with nearest-first fallback if ranking fails.
- Sends Telegram HTML output with escaped dynamic text and KakaoMap links.

## Architecture

Entry point:

- `bot.py` builds the Telegram application, wires dependencies into
  `application.bot_data`, registers handlers, and starts long polling.

Core package:

- `foodbot.config` loads environment-based configuration and default trigger phrases.
- `foodbot.handlers` contains Telegram command, callback, and text handlers.
- `foodbot.session` stores in-memory per-chat sessions with lazy timeout expiry.
- `foodbot.pipeline` orchestrates extraction, area resolution, place search, ranking,
  and message formatting.
- `foodbot.llm` wraps Gemini calls and parses strict JSON responses.
- `foodbot.places` wraps Kakao keyword search and normalizes place results.
- `foodbot.geo` resolves named areas to coordinates through Kakao search.
- `foodbot.dictionary` provides a small Russian-to-Korean fallback craving map.
- `foodbot.formatting` builds the final Telegram HTML message.

## Runtime Flow

1. A user sends a trigger phrase or `/eat`.
2. The bot creates a `Session` for that chat and sends a prompt with an inline button.
3. While the session is active, non-command text messages are appended to the session.
4. A user sends `/go` or taps the button.
5. The session is ended and the stale inline keyboard is removed if possible.
6. `pipeline.run` processes the collected messages:
   - Gemini extracts cravings, Korean search queries, area, and no-preference state.
   - If extraction fails, `dictionary.translate_cravings` is used as a fallback.
   - If an area was extracted, Kakao geocoding resolves it to a search center.
   - Kakao searches each query near the selected point.
   - If no results are found, the search radius is doubled once.
   - Gemini ranks places; if ranking fails, the nearest places are selected.
7. The formatted recommendation message is sent to Telegram.

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
- `TRIGGER_PHRASES`, comma-separated override for the built-in Russian triggers

Configuration is loaded from `.env` plus process environment through
`python-dotenv`.

## External Services

- Telegram Bot API via `python-telegram-bot`.
- Gemini via `google-genai`.
- Kakao Local API via `httpx`.

The bot uses long polling, so it is online only while `python bot.py` is running.

## Tests

The test suite is under `tests/` and uses `pytest` plus `pytest-asyncio`.
It covers:

- Config defaults, overrides, and missing required values.
- Session lifecycle, trigger matching, and timeout expiry.
- Telegram handler behavior for starting sessions, collecting messages, empty
  sessions, pipeline invocation, keyboard cleanup, and HTML parse mode.
- LLM JSON parsing and fallback behavior.
- Kakao response parsing and place merging.
- Pipeline happy path, no-preference nudges, no-result responses, dictionary
  fallback, and ranking fallback.
- HTML escaping and message formatting.
- Area resolution fallback.

Run tests with:

```powershell
python -m pytest -v
```

## Current Limitations

- Sessions are in-memory only; restarting the process loses active sessions.
- There is no database or admin interface.
- Search quality depends on Gemini extraction and Kakao keyword results.
- The fallback dictionary is intentionally small and only covers common cravings.
- Area resolution uses Kakao keyword search, not a dedicated administrative boundary
  database.
- Kakao and Gemini errors are handled with graceful fallback where possible, but API
  credentials and network access are still required for full functionality.

## Development Notes

Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

Install test dependencies:

```powershell
pip install -r requirements-dev.txt
```

Run the bot locally:

```powershell
python bot.py
```

The repository is intentionally compact. Most behavior is isolated behind small
modules, making it straightforward to swap the LLM provider, place provider, or
session storage without rewriting Telegram handler code.
