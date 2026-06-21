# Fix Plan

Branch: `fix`

Baseline:

- Test command: `.\\.venv\\Scripts\\python.exe -m pytest -v`
- Original result before fixes: 38 passed
- Current result after fixes: 53 passed
- Note: pytest reported a cache write warning for `.pytest_cache`, but tests passed.

Implementation status: completed on branch `fix`.

## Goals

Make the first version safer for real group use without changing the main product
behavior:

- Keep the Telegram group flow simple.
- Preserve Gemini and Kakao fallbacks.
- Make failures observable and user-visible when appropriate.
- Add tests for the risky paths found in review.

## Phase 1: Provider Lifecycle And Error Semantics

### 1. Close Kakao HTTP Client On Shutdown

Problem:

- `KakaoClient` owns an `httpx.AsyncClient`, but `bot.py` never closes it.

Implementation:

- Add an async shutdown callback in `bot.py`.
- Read `app.bot_data["kakao"]`.
- If the object has `aclose`, await it.
- Register the callback with the Telegram application lifecycle.

Tests:

- Add a test that builds an app with a fake Kakao client and verifies shutdown calls
  `aclose`.
- If direct lifecycle testing is awkward, extract a small `close_resources(bot_data)`
  helper and test that helper.

### 2. Distinguish No Results From Provider Failure

Problem:

- `pipeline._search_all` catches all search exceptions and returns an empty result
  set. Invalid API keys, rate limits, and network failures look like "nothing found."

Implementation:

- Track per-query search failures.
- Log failed query, search point, radius, and exception class.
- If every Kakao search attempt fails, return a provider-error message instead of
  `NOT_FOUND`.
- Keep current behavior when at least one query succeeds but returns no places.

Tests:

- All searches fail: returns a temporary error message.
- Some searches fail and some succeed: still formats successful results.
- All searches succeed with empty lists: still returns `NOT_FOUND`.

## Phase 2: Callback Safety

### 3. Reject Stale Inline Buttons

Problem:

- Any callback with `callback_data="find"` can submit the current chat session.
- If an old inline keyboard survives, tapping it can finish a newer session.

Implementation:

- In `on_go`, when handling a callback, compare
  `update.callback_query.message.message_id` with `session.prompt_message_id`.
- If they do not match, answer the callback with a short stale-button alert and do
  not end the session.
- Keep `/go` command behavior unchanged because it has no message id to compare.

Tests:

- Callback from the active prompt submits normally.
- Callback from an old prompt is rejected.
- Rejected stale callback does not clear messages or end the active session.

## Phase 3: Input And LLM Schema Hardening

### 4. Validate Gemini Extraction Shape

Problem:

- `parse_extract` converts whatever is in `search_queries` with `list(...)`.
- A string response becomes a list of characters.

Implementation:

- Validate decoded JSON is an object.
- Validate `cravings` and `search_queries` are lists.
- Keep only non-empty strings.
- Normalize `area` to a stripped string or `None`.
- Validate `no_preference` is boolean-like only if needed; otherwise default safely.
- Raise `ValueError` on malformed schema so pipeline fallback can run.

Tests:

- String `search_queries` is rejected.
- Non-object JSON is rejected.
- Empty or whitespace query strings are ignored.
- Valid responses still parse as before.

### 5. Deduplicate And Limit Ranking Picks

Problem:

- `parse_ranking` filters invalid indexes but allows duplicates and more picks than
  requested.

Implementation:

- Add a `limit` argument to `parse_ranking`, or trim in `GeminiLLM.rank_places`.
- Deduplicate by place index while preserving LLM order.
- Return at most `count` picks.

Tests:

- Duplicate indexes return once.
- More than `count` picks are trimmed.
- Invalid indexes are still ignored.

### 6. Bound Session Input

Problem:

- Active sessions can collect unlimited messages and text length.

Implementation:

- Add config values with conservative defaults:
  - `MAX_SESSION_MESSAGES`, for example `50`.
  - `MAX_SESSION_CHARS`, for example `4000`.
- Enforce limits in `Session.add_message` or in the handler before adding messages.
- Prefer preserving the earliest useful messages and ignoring excess input.
- Optionally notify the chat when the limit is reached.

Tests:

- Blank messages are still ignored.
- Messages over the limit are not appended.
- Total character cap is enforced.
- Existing session tests still pass with default limits.

## Phase 4: Configuration Validation

### 7. Parse Config With Clear Errors

Problem:

- Numeric config values can raise raw `ValueError`.
- Invalid values such as `RESULTS_COUNT=0` or negative radius are accepted.

Implementation:

- Add helper parsers for required floats and optional positive ints.
- Raise `ConfigError` with the env var name and expected value shape.
- Validate:
  - latitude is between `-90` and `90`;
  - longitude is between `-180` and `180`;
  - radius, results count, timeout, and max session limits are positive;
  - results count is within a practical upper bound.

Tests:

- Bad float raises `ConfigError`.
- Bad int raises `ConfigError`.
- Zero or negative tuning values raise `ConfigError`.
- Valid overrides still load correctly.

## Phase 5: Polish And Documentation

### 8. Update README And Project Overview

Implementation:

- Document new optional config values.
- Mention that provider failures return a temporary error instead of "nothing found."
- Keep setup instructions aligned with `.env.example`.

Tests:

- No code tests required.
- Manually check `.env.example`, `README.md`, and `PROJECT_OVERVIEW.md` agree.

## Suggested Order

1. Add tests for each reviewed failure mode as failing tests.
2. Implement callback safety and LLM schema validation first; they are tightly scoped.
3. Implement provider failure handling and logging.
4. Add shutdown cleanup.
5. Add config and session bounds.
6. Update docs.
7. Run `.\\.venv\\Scripts\\python.exe -m pytest -v`.

## Definition Of Done

- All tests pass.
- New tests cover each review finding.
- No secrets are read from or written to `.env`.
- Existing Telegram user flow remains unchanged for normal use.
- Error messages distinguish user input problems, no nearby results, and temporary
  provider failures.
