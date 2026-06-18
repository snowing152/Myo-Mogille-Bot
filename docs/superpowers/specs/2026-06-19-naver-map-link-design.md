# Naver Map Link — Design Spec

- **Date:** 2026-06-19
- **Status:** Approved (design), pending implementation plan
- **Project folder:** `myo_mogille`

## Problem

Each place result currently links only to Kakao Map (`place.url`, from the Kakao
Local Search response). Some group members prefer Naver Map. We want a second,
labeled link per result so people can open whichever map app they use.

## Research Findings (why this is simpler than first planned)

The original plan was to call Naver's Local Search API and match results to the
chosen place for a precise deep link. Investigation showed this doesn't actually
work:

- Naver's only documented deep-link scheme is `nmap://search?query=...`, an
  **app-only intent** — useless for someone without the Naver Map app installed
  (e.g. Telegram Desktop users).
- The Local Search API's `link` field is typically the business's **own
  homepage**, not a Naver Map page, and is frequently empty.
- A real Naver Map page (`map.naver.com/p/search/<query>/place/<place_id>`)
  needs a `place_id` the Local Search API doesn't return; getting one would mean
  scraping Naver Map's JS-heavy site — fragile and out of scope.

**Decision:** skip the Naver API entirely. Build a best-effort, deterministic
search-by-name URL: `https://map.naver.com/p/search/<url-encoded place name>`.
No API key, no network call, no failure mode — but it's unverified by automated
tools (Naver Map is a JS SPA WebFetch can't render), so a manual check in
Telegram is the acceptance test (see Testing).

## Design

### `foodbot/places.py`

Add a pure helper:

```python
from urllib.parse import quote

def naver_search_url(name: str) -> str:
    return f"https://map.naver.com/p/search/{quote(name)}"
```

### `foodbot/formatting.py`

Switch the message from plain text to Telegram **HTML** parse mode so links can
be wrapped in clickable text ("тык сюда") with a colored-circle icon per
provider, instead of showing bare URLs:

```
1. 하남돼지집 홍대입구역점 (음식점 > 한식 > 고기,육류 > 돼지고기)
короткая причина
🟡 Kakao: тык сюда
🟢 Naver: тык сюда
```

- All dynamic text (place name, category, reason, area label) is passed through
  `html.escape()` before being embedded, since it originates from Kakao/LLM
  output we don't control.
- The Kakao line is only shown if `place.url` is non-empty (defensive; Kakao
  almost always returns one). The Naver line is always shown since it's
  deterministic.
- Update the module docstring — it currently says "no Markdown → no escaping
  pitfalls"; that's no longer true now that we use HTML formatting with
  explicit escaping.

### `foodbot/handlers.py`

The single `send_message` call in `on_go` that sends the final pipeline result
needs `parse_mode="HTML"`. This is safe for all of `pipeline.run()`'s possible
return values (the formatted result, `NUDGE`, `NOT_FOUND`, or `handlers.ERROR`)
since none of the plain-text fallback strings contain `<`, `>`, or `&`.

## Testing

- `tests/test_places.py`: unit test `naver_search_url()` for correct URL
  encoding (spaces, Korean characters).
- `tests/test_formatting.py`: update to assert both labeled links appear, with
  `html.escape()` applied to dynamic content, and that the Kakao line is
  omitted when `place.url` is empty.
- **Manual acceptance test:** after implementing, trigger a real round in
  Telegram and tap a generated Naver link to confirm it opens an actual Naver
  Map search results page (not an error) — this can't be verified by automated
  tools.

## Non-Goals

- Naver API integration / precise place matching (ruled out above).
- Configurable icon style (decided: colored circles, 🟡/🟢).
