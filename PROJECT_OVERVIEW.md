# Project Overview Myo Mogille Bot

## Purpose

This project is a Telegram group-chat bot for helping friends decide where to eat.
When someone starts a food-planning session with `/eat` or a trigger phrase such as
"куда пойдем кушать?", the bot collects group messages. A user then sends `/go` or
taps the inline button, and the bot extracts food and drink preferences, searches
nearby Korean restaurants, and replies with a short list of recommended places.

The current product focus is Russian-language chat input for groups in Korea. Search
queries are converted to Korean terms, expanded into Korean place-intent searches,
and then used with Kakao Places. Optional Naver Blog Search snippets can add
supporting evidence for foods, possible prices, and atmosphere hints.

## Main Capabilities

- Starts a per-chat collection session from `/eat` or configured trigger phrases.
- Collects free-text cravings from group members during the active session.
- Notifies the group once if the session input limit has been reached.
- Lets anyone finish the session with `/go` or the inline find-places button.
- Rejects stale inline buttons from older session prompts.
- Uses Gemini to extract cravings, Korean search queries, and an optional area.
- Uses Kakao local keyword search to find restaurants near the default or resolved
  area.
- Expands exact food terms into broader place-intent queries such as `전집`,
  `막걸리집`, `주막`, and `요리주점`.
- Optionally uses Naver Blog Search snippets as ranking/output evidence.
- Uses deterministic evidence scoring plus Gemini ranking, with scored-order
  fallback if ranking fails.
- Distinguishes provider outages from genuine empty search results.
- Sends Telegram HTML output with escaped dynamic text and KakaoMap links.

## Architecture

Entry point:

- `bot.py` builds the Telegram application, wires dependencies into
  `application.bot_data`, registers handlers, and starts long polling.

Core package:

- `foodbot.config` loads and validates environment-based configuration and default
  trigger phrases.
- `foodbot.handlers` contains Telegram command, callback, and text handlers.
- `foodbot.session` stores bounded in-memory per-chat sessions with lazy timeout
  expiry.
- `foodbot.pipeline` orchestrates extraction, area resolution, place search, ranking,
  and message formatting.
- `foodbot.llm` wraps Gemini calls and parses strict JSON responses.
- `foodbot.places` wraps Kakao keyword search and normalizes place results.
- `foodbot.naver` wraps Naver Search API calls and normalizes blog/local results.
- `foodbot.evidence` extracts food terms, possible prices, and hints from blog
  snippets.
- `foodbot.search_queries` expands Korean search terms into place-intent queries.
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
   - Exact Korean queries are expanded into place-intent search terms.
   - Kakao searches each expanded query near the selected point.
   - If no results are found, the search radius is doubled once.
   - Search provenance tracks which query found each place and its best result rank.
   - Optional Naver Blog Search snippets are collected for top candidates.
   - Candidates are scored with distance, query evidence, and blog evidence.
   - Gemini ranks places with evidence lines; if ranking fails, scored order is used.
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
- `MAX_SESSION_MESSAGES`, default `50`
- `MAX_SESSION_CHARS`, default `4000`
- `NAVER_CLIENT_ID`, optional
- `NAVER_CLIENT_SECRET`, optional
- `NAVER_BLOG_EVIDENCE_ENABLED`, default `false`
- `NAVER_BLOG_EVIDENCE_LIMIT`, default `3`

Configuration is loaded from `.env` plus process environment through
`python-dotenv`.

## External Services

- Telegram Bot API via `python-telegram-bot`.
- Gemini via `google-genai`.
- Kakao Local API via `httpx`.
- Optional Naver Search API via `httpx`.

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
- Naver response parsing and blog evidence extraction.
- Pipeline happy path, no-preference nudges, no-result responses, dictionary
  fallback, blog-evidence fallback, and ranking fallback.
- HTML escaping and message formatting.
- Area resolution fallback.

Run tests with:

```powershell
python -m pytest -v
```

## Current Limitations

- Sessions are in-memory only; restarting the process loses active sessions.
- There is no database or admin interface.
- Search quality depends on Gemini extraction, Kakao keyword results, and limited
  Naver blog snippets when evidence is enabled.
- Naver evidence uses official search snippets, not full review scraping, so food
  and price details are only shown when visible in the snippet data.
- The fallback dictionary is intentionally small and only covers common cravings.
- Area resolution uses Kakao keyword search, not a dedicated administrative boundary
  database.
- Kakao, Gemini, and optional Naver errors are handled with graceful fallback where
  possible, but API credentials and network access are still required for full
  functionality.
- Sessions are bounded by message count and total character count to control prompt
  size and cost.

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
