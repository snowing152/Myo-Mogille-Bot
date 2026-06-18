# Naver Map Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second, labeled Naver Map link next to the existing Kakao Map link in each place result, using clickable link text ("тык сюда") and brand-colored emoji icons instead of bare URLs.

**Architecture:** A pure URL-builder (`naver_search_url`) in `foodbot/places.py` constructs a deterministic `map.naver.com` search-by-name link — no API key, no network call. `foodbot/formatting.py` switches its output from plain text to Telegram HTML (escaping all dynamic text), wrapping both links in `<a href="...">тык сюда</a>` with `🟡 Kakao:` / `🟢 Naver:` labels. `foodbot/handlers.py` sends that final message with `parse_mode=ParseMode.HTML`.

**Tech Stack:** Python 3.14, `python-telegram-bot`, `urllib.parse.quote`, `html.escape`, pytest/pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-06-19-naver-map-link-design.md`

---

### Task 1: `naver_search_url()` helper

**Files:**
- Modify: `foodbot/places.py`
- Test: `tests/test_places.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_places.py` (the file currently ends after `test_kakao_search_builds_request`, line 67):

```python


def test_naver_search_url_encodes_ascii_name():
    from foodbot.places import naver_search_url

    assert naver_search_url("Cafe Mama") == "https://map.naver.com/p/search/Cafe%20Mama"


def test_naver_search_url_encodes_korean_name():
    from urllib.parse import quote

    from foodbot.places import naver_search_url

    name = "이자카야 하나"
    assert naver_search_url(name) == f"https://map.naver.com/p/search/{quote(name)}"
```

(Local imports inside the test functions are intentional here so the existing top-of-file import line doesn't need touching until Step 3 — keep it that way, don't move them up yet.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_places.py -v`
Expected: the two new tests FAIL with `ImportError: cannot import name 'naver_search_url' from 'foodbot.places'`

- [ ] **Step 3: Implement `naver_search_url`**

In `foodbot/places.py`, change the import block at the top (lines 1-5) from:

```python
from __future__ import annotations

from dataclasses import dataclass

import httpx
```

to:

```python
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx
```

Then add this function right after the `KAKAO_KEYWORD_URL` constant (after line 7, before the `Place` dataclass):

```python
def naver_search_url(name: str) -> str:
    """Best-effort Naver Map search-by-name link (no API, no guaranteed exact match)."""
    return f"https://map.naver.com/p/search/{quote(name)}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_places.py -v`
Expected: all tests PASS (5 total: the 3 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add foodbot/places.py tests/test_places.py
git commit -m "feat: add naver_search_url helper for best-effort Naver Map links"
```

---

### Task 2: HTML-formatted message with Kakao + Naver links

**Files:**
- Modify: `foodbot/formatting.py`
- Test: `tests/test_formatting.py`

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `tests/test_formatting.py` with:

```python
from foodbot.places import Place
from foodbot.llm import Pick
from foodbot.formatting import build_message

PLACES = [
    Place("1", "이자카야 하나", "술집", "주소", 37.5, 127.0, 250, "http://map/1"),
    Place("2", "삼겹살집", "고기", "주소", 37.5, 127.0, 400, "http://map/2"),
]


def test_build_message_lists_picks():
    msg = build_message("홍대", PLACES, [Pick(0, "соджу + закуски"), Pick(1, "мясо")])
    assert "홍대" in msg
    assert "이자카야 하나" in msg
    assert "삼겹살집" in msg
    assert "соджу + закуски" in msg
    assert msg.count("🟡 Kakao:") == 2
    assert msg.count("🟢 Naver:") == 2
    assert msg.count("тык сюда") == 4  # 2 places x 2 links
    assert '<a href="http://map/1">тык сюда</a>' in msg
    assert '<a href="http://map/2">тык сюда</a>' in msg


def test_build_message_includes_naver_search_link():
    from foodbot.places import naver_search_url

    msg = build_message("홍대", PLACES, [Pick(0, "соджу")])
    expected_naver_url = naver_search_url("이자카야 하나")
    assert f'<a href="{expected_naver_url}">тык сюда</a>' in msg


def test_build_message_omits_kakao_line_when_url_empty():
    place_no_url = Place("3", "노 링크집", "식당", "주소", 37.5, 127.0, 100, "")
    msg = build_message("홍대", [place_no_url], [Pick(0, "что-то")])
    assert "🟡 Kakao:" not in msg
    assert "🟢 Naver:" in msg


def test_build_message_escapes_html_special_characters():
    place = Place("4", "Bar & Grill <Best>", "food", "addr", 37.5, 127.0, 100, "http://map/4")
    msg = build_message("홍대", [place], [Pick(0, "острое & вкусное")])
    assert "Bar &amp; Grill &lt;Best&gt;" in msg
    assert "острое &amp; вкусное" in msg
    assert "Bar & Grill <Best>" not in msg  # raw, unescaped text must not appear


def test_build_message_empty():
    msg = build_message("홍대", PLACES, [])
    assert "Ничего" in msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_formatting.py -v`
Expected: `test_build_message_lists_picks`, `test_build_message_includes_naver_search_link`, `test_build_message_omits_kakao_line_when_url_empty`, and `test_build_message_escapes_html_special_characters` FAIL (no Naver link, no icons/labels, no escaping in current output). `test_build_message_empty` still PASSes.

- [ ] **Step 3: Implement the HTML-formatted `build_message`**

Replace the entire contents of `foodbot/formatting.py` with:

```python
from __future__ import annotations

import html

from foodbot.places import Place, naver_search_url
from foodbot.llm import Pick


def build_message(area_label: str, places: list[Place], picks: list[Pick]) -> str:
    """Telegram HTML-formatted Russian message.

    Dynamic text (place name/category/reason/area) is html-escaped since it
    originates from Kakao/LLM output we don't control. Must be sent with
    parse_mode="HTML" (see foodbot/handlers.py).
    """
    if not picks:
        return "Ничего подходящего не нашёл 😕 Попробуйте другие пожелания или район."

    header = f"Нашёл {len(picks)} мест рядом (район: {html.escape(area_label)}) 👇"
    blocks: list[str] = []
    for number, pick in enumerate(picks, start=1):
        place = places[pick.index]
        reason = pick.reason_ru or place.category
        head = f"{number}. {html.escape(place.name)}"
        if place.category:
            head += f" ({html.escape(place.category)})"
        block = head
        if reason:
            block += f"\n{html.escape(reason)}"
        if place.url:
            block += f'\n🟡 Kakao: <a href="{html.escape(place.url)}">тык сюда</a>'
        naver_url = naver_search_url(place.name)
        block += f'\n🟢 Naver: <a href="{html.escape(naver_url)}">тык сюда</a>'
        blocks.append(block)

    return header + "\n\n" + "\n\n".join(blocks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_formatting.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: all tests PASS (no other module depends on the old plain-text format)

- [ ] **Step 6: Commit**

```bash
git add foodbot/formatting.py tests/test_formatting.py
git commit -m "feat: format results as HTML with Kakao + Naver map links"
```

---

### Task 3: Send the result message with `parse_mode=HTML`

**Files:**
- Modify: `foodbot/handlers.py`
- Test: `tests/test_handlers.py`

- [ ] **Step 1: Write the failing test**

Add to the bottom of `tests/test_handlers.py`:

```python


async def test_on_go_sends_result_with_html_parse_mode(monkeypatch):
    from telegram.constants import ParseMode

    ctx = _context()
    store = ctx.application.bot_data["sessions"]
    store.start(1)
    store.get_active(1).add_message("хочу соджу")

    async def fake_run(messages, deps):
        return "РЕЗУЛЬТАТ"

    monkeypatch.setattr(pipeline, "run", fake_run)
    upd, _ = _update(1, callback=True)
    await handlers.on_go(upd, ctx)

    final_call = ctx.bot.send_message.await_args_list[-1]
    assert final_call.kwargs.get("text") == "РЕЗУЛЬТАТ"
    assert final_call.kwargs.get("parse_mode") == ParseMode.HTML
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_handlers.py::test_on_go_sends_result_with_html_parse_mode -v`
Expected: FAIL — `assert None == <ParseMode.HTML: 'HTML'>` (current code doesn't pass `parse_mode`)

- [ ] **Step 3: Add `parse_mode=ParseMode.HTML` to the final send**

In `foodbot/handlers.py`, add the import to the top of the file (after line 5's `from telegram import ...`):

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
```

Then change the last line of `on_go` (currently line 102):

```python
    await context.bot.send_message(chat_id=chat_id, text=reply)
```

to:

```python
    await context.bot.send_message(chat_id=chat_id, text=reply, parse_mode=ParseMode.HTML)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_handlers.py -v`
Expected: all tests PASS, including the new one

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add foodbot/handlers.py tests/test_handlers.py
git commit -m "feat: send place results with HTML parse mode"
```

---

### Task 4: Manual acceptance test (cannot be automated)

**Why:** Naver Map is a JS-heavy single-page app; no automated tool here (WebFetch, pytest) can confirm the generated `map.naver.com/p/search/<name>` URL actually renders a working search page instead of an error. This must be checked by hand once, live.

- [ ] **Step 1: Run the bot**

Run: `.\.venv\Scripts\python.exe bot.py`

- [ ] **Step 2: Trigger a full round in your Telegram group**

Send the trigger phrase (e.g. `куда пойдём кушать?`), type a craving (e.g. `хочу мясо`), then tap 🍽 Найти места.

- [ ] **Step 3: Verify the message renders correctly**

Confirm each result shows `🟡 Kakao: тык сюда` and `🟢 Naver: тык сюда` as tappable links (not raw `<a href...>` markup — if raw HTML tags are visible as text, `parse_mode` isn't being applied correctly and Task 3 needs revisiting).

- [ ] **Step 4: Tap a Naver link**

Confirm it opens `map.naver.com` in a browser (or the Naver Map app, if installed) and shows search results for that place's name — not a 404 or blank error page.

- [ ] **Step 5: Report back**

If the Naver link doesn't work as expected, note exactly what happened (error page, blank page, wrong content) so the URL-building approach in Task 1 can be revisited.

---

## Self-Review Notes

- **Spec coverage:** `naver_search_url` (Task 1) ✓, HTML formatting with escaping/icons/link-text (Task 2) ✓, `parse_mode="HTML"` on the result send (Task 3) ✓, manual acceptance test (Task 4) ✓, docstring update (Task 2, Step 3) ✓. Non-goals (Naver API integration, configurable icons) correctly have no tasks.
- **Type consistency:** `naver_search_url(name: str) -> str` defined in Task 1 is called identically in Task 2's `formatting.py` and in the Task 1/2 tests — no signature drift.
- **No placeholders:** every step has complete, runnable code or an exact command with expected output.
