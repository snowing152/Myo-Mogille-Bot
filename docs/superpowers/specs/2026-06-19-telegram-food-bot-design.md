# Telegram Food-Decider Bot — Design Spec

- **Date:** 2026-06-19
- **Status:** Approved (design), pending implementation plan
- **Project folder:** `myo_mogille`

## Problem

A group of friends (chatting in Russian, living in Korea) wastes days or weeks
deciding where to go eat/drink. Today they manually browse KakaoMap/NaverMap,
read menus, and compare — for everyone's differing cravings. We want a Telegram
bot that lives in the group chat, reads the cravings when someone asks "куда
пойдём кушать?", and returns a short, matched shortlist of nearby places with
direct map links.

## Goals

- Live in the group chat; trigger on a natural Russian phrase.
- Collect each person's free-form cravings (soju, kimchi, BBQ, …).
- Turn the messy multi-person Russian chat into a small set of restaurant
  suggestions near the group, each with a tappable KakaoMap link.
- Be effectively free to run at the group's volume.

## Non-Goals (explicitly out of scope for now)

- Scraping exact menus/prices (fragile; the map link covers this).
- AI price estimates (decided against — link only).
- Booking/reservations.
- Multi-group SaaS / public distribution. This is for one friend group.
- 24/7 hosting (runs on the owner's PC for now).

## User Experience (the whole product, end to end)

1. **Sasha:** `куда пойдем кушать?`
2. **Bot:** "Окей, собираю пожелания! Пишите что хотите — соджу, кимчи, мясо…
   Когда готовы — жмите кнопку." with an inline button 〔🍽 Найти места〕
3. Members type cravings freely: `хочу соджу`, `и кимчи`, `можно мясо пожарить`.
4. *(Optional)* someone names another area in chat (e.g. `давайте в Хондэ`) to
   search somewhere other than the default area.
5. Anyone taps 〔🍽 Найти места〕.
6. **Bot** replies in Russian with ~3 matched places:
   - place name (Korean, as on the map) · type · distance from search center
   - one short Russian line: *why this place matches the group's cravings*
   - a tappable KakaoMap link (real menu, photos, price, reviews, hours)

The bot's value: it reads the chaotic chat and hands back a short, matched
shortlist, replacing 30 minutes of manual map-scrolling.

## Architecture

Python 3.11+, runs on the owner's PC using Telegram **long-polling** (no public
URL, webhook, or server required). Single process, single bot.

### Modules

Each module is small and single-purpose so it can be understood and tested
independently. Handlers stay thin; real logic lives in testable modules.

| Module | Responsibility |
|---|---|
| `bot.py` | Entry point. Builds the Telegram app, registers handlers, starts polling. |
| `foodbot/config.py` | Load secrets + settings from `.env`. Validate required keys at startup. |
| `foodbot/session.py` | Per-chat "eat session" state machine (`idle → collecting → done`). Stores collected craving messages, optional area override, start time. In-memory dict keyed by `chat_id`. |
| `foodbot/handlers.py` | Telegram glue: detect trigger → start session; collect messages while `collecting`; handle the "Найти места" button. Delegates real work to other modules. |
| `foodbot/llm.py` | Provider-agnostic AI wrapper (Gemini 2.5 Flash now). Two functions: `extract_cravings()` and `rank_places()`. Returns structured data. |
| `foodbot/places.py` | Kakao Local API client. Keyword-search around coordinates → list of `Place` objects. |
| `foodbot/geo.py` | Resolve a default area, a named neighborhood (via Kakao), or (later) a 📍 pin into coordinates. |
| `foodbot/formatting.py` | Build the final Russian Telegram message from real place data + LLM reasons. |
| `foodbot/dictionary.py` | Small craving→Korean fallback map, used only when the LLM is unavailable. |
| `foodbot/pipeline.py` | Orchestrates the search flow (extract → search → rank → format). Pure-ish, easy to test with mocks. |

### Project layout

```
myo_mogille/
  bot.py
  foodbot/
    __init__.py
    config.py
    session.py
    handlers.py
    llm.py
    places.py
    geo.py
    formatting.py
    dictionary.py
    pipeline.py
  tests/
    test_session.py
    test_places.py
    test_llm.py
    test_formatting.py
    test_pipeline.py
    test_dictionary.py
  .env.example
  .gitignore
  requirements.txt
  README.md
  docs/superpowers/specs/2026-06-19-telegram-food-bot-design.md
```

## Data Flow

1. **Trigger.** A group message matches a trigger phrase (or `/eat`). `session`
   for that `chat_id` moves to `collecting`; the bot replies with the prompt +
   inline "Найти места" button.
2. **Collect.** Every subsequent human text message in that chat (not the bot's,
   not commands) is appended to `session.messages` while `collecting`.
3. **Finalize.** Someone taps the button (or sends `/go`). `pipeline.run()`:
   1. `llm.extract_cravings(messages)` → `{cravings, search_queries, area?,
      no_preference}` (Russian chat → Korean search queries).
   2. Resolve the search center: named `area` (via `geo`) → else the configured
      default area.
   3. For each `search_query`, `places.search(query, lat, lng, radius)`; merge
      and de-duplicate results; sort by distance; cap to ~20 candidates.
   4. `llm.rank_places(cravings, candidates)` → selects the best ~3 **by index**
      and writes a short Russian reason for each. The LLM only selects and
      explains; place names/links/distances always come from real Kakao data, so
      it cannot invent a restaurant or a link.
   5. `formatting.build_message(...)` → final Russian message.
4. **Reply & reset.** Send the message; session returns to `idle`.

## LLM Design

- **Provider-agnostic interface.** `llm.py` exposes `extract_cravings()` and
  `rank_places()`. Implementation uses Gemini 2.5 Flash via the `google-genai`
  SDK (`LLM_MODEL` env, default `gemini-2.5-flash`). Swapping providers means
  editing one module, not the bot.
- **Structured output.** Both calls request strict JSON and parse it. Example
  for extraction:
  ```json
  {
    "cravings": ["soju", "kimchi", "grilled pork"],
    "search_queries": ["이자카야", "김치찌개", "삼겹살"],
    "area": "홍대",
    "no_preference": false
  }
  ```
  Example for ranking:
  ```json
  { "picks": [ {"index": 0, "reason_ru": "соджу + закуски"},
               {"index": 3, "reason_ru": "삼겹살 — мясо пожарить"} ] }
  ```
- **Two calls per session** (~4k input + ~0.8k output tokens total). At realistic
  volume this is within Gemini's free tier → **$0/month**; even on the paid tier
  it is ~$0.15–0.20/month.

## Place Search (Kakao Local)

- Endpoint: `GET https://dapi.kakao.com/v2/local/search/keyword.json`
- Params: `query`, `x` (longitude), `y` (latitude), `radius` (meters, default
  `SEARCH_RADIUS_M=1500`, max 20000), `sort=distance`, `size=15`.
- Header: `Authorization: KakaoAK {KAKAO_REST_API_KEY}`.
- Parsed `Place` fields: `name` (`place_name`), `category` (`category_name`),
  `address` (`road_address_name`/`address_name`), `lat`/`lng` (`y`/`x`),
  `distance` (int meters), `url` (`place_url`), `phone`.
- One search per query; merge + dedupe by Kakao place id; sort by distance.

## Location Handling

- **Default area:** `DEFAULT_LAT`, `DEFAULT_LNG`, `DEFAULT_AREA_NAME` from config
  (e.g. near campus). Used when no override is given.
- **Named neighborhood override (MVP):** if `extract_cravings()` returns an
  `area` string, `geo.resolve_area()` resolves it to coordinates via Kakao
  keyword/address search; on failure it falls back to the default area.
- **📍 Pin override:** post-MVP.

## Session State Machine

- States: `idle`, `collecting`, `done` (transient during the pipeline).
- One active session per chat. A new trigger while `collecting` re-anchors the
  current session (forgiving rather than rejecting).
- **Expiry:** `SESSION_TIMEOUT_MIN` (default 20). Checked lazily — if the button
  is pressed after expiry, the bot says the session expired and to start again.
- Collected messages exclude the bot's own messages and any `/command` messages.

## Configuration (`.env`)

| Key | Purpose | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot auth (from BotFather) | — (required) |
| `GEMINI_API_KEY` | Google AI Studio key | — (required) |
| `KAKAO_REST_API_KEY` | Kakao Developers REST key | — (required) |
| `DEFAULT_LAT` / `DEFAULT_LNG` | Default search center | — (required) |
| `DEFAULT_AREA_NAME` | Human label for default area | — (required) |
| `SEARCH_RADIUS_M` | Search radius (meters) | `1500` |
| `RESULTS_COUNT` | How many places to return | `3` |
| `SESSION_TIMEOUT_MIN` | Collection window before expiry | `20` |
| `LLM_MODEL` | Model id | `gemini-2.5-flash` |
| `TRIGGER_PHRASES` | Optional comma-separated override | built-in list |

`.env` is git-ignored; `.env.example` is committed.

## Trigger Detection

- Case-insensitive substring match, with `ё`/`е` normalized.
- Built-in default phrases: "куда пойдем кушать", "куда пойдем поесть",
  "где поедим", "пойдем кушать", "пойдем есть", "куда пойти поесть".
- `/eat` command is an always-reliable alternative trigger.

## Error Handling & Degraded Modes

- **No cravings** (`no_preference: true`): nudge — "Напишите, что хотите поесть
  или выпить, потом жмите кнопку."
- **LLM unavailable:** retry once; if still failing, fall back to
  `dictionary.py` to translate recognized craving words (соджу→소주, кимчи→김치,
  пиво→맥주, мясо→삼겹살, …) into Korean queries so the bot still works in a
  reduced way. Ranking then falls back to "nearest first."
- **No Kakao results** for all queries: widen the radius once (×2) and retry;
  still nothing → "Ничего не нашёл рядом, попробуйте другой район или другие
  пожелания."
- **Network/timeout/HTTP errors:** caught, logged, friendly Russian error reply.

## Setup Requirements (all free)

1. **Telegram bot token** — already obtained.
2. **Disable privacy mode** in @BotFather (`/setprivacy → Disable`). *Critical:*
   without this the bot can only see commands/mentions, not the craving
   messages. (Alternative: make the bot a group admin.)
3. **Kakao REST API key** — free at developers.kakao.com.
4. **Gemini API key** — free at Google AI Studio.

## Testing Strategy

- Pure logic unit-tested directly: trigger detection, session transitions +
  expiry, Kakao JSON parsing/dedup, message formatting, dictionary fallback.
- `llm.py` and `places.py`: HTTP/SDK calls mocked; assert request shape and
  response parsing against sample payloads.
- `pipeline.run()`: tested end-to-end with `llm` and `places` mocked.
- Handlers kept thin; logic lives in modules so tests avoid Telegram plumbing.
- `pytest` as the runner.

## Scope

**MVP (first build):** trigger → collect → button → Kakao search → AI-matched
top 3 in Russian, with default area + named-neighborhood override, plus the
dictionary fallback and error handling above.

**Later (easy add-ons, enabled by the module boundaries):**
- 📍 location-pin override.
- Naver as a second place source behind the `places` boundary.
- `/sethome` to change the default area from chat.
- "Показать ещё 3" button for more options.
- Deploy to a free 24/7 host (Railway/Render/Fly/VPS).

## Key Decisions & Alternatives

- **Kakao first, Naver later.** Kakao keyword search returns coordinates,
  distance, and clean map links with a large free quota; Naver local caps at 5
  results and links to homepages. The `places` boundary makes Naver an easy
  second source later.
- **Replies in Russian**, Korean place names kept verbatim (so they match the
  map).
- **Gemini 2.5 Flash to start**, behind a provider-agnostic wrapper — chosen for
  free tier, speed, strong Russian+Korean, and reliable JSON output.
- **In-memory session state.** Single-process PC bot; persistence is unnecessary
  now and would add complexity (YAGNI). A restart simply clears in-progress
  sessions.
- **Long-polling, not webhooks.** No public URL needed; ideal for running on a
  PC.
