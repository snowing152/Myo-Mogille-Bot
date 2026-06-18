# Telegram Food-Decider Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram group-chat bot that, when someone asks "куда пойдём кушать?", collects everyone's free-form Russian cravings, turns them into Korean restaurant searches, and replies with ~3 matched nearby places (name, type, distance, KakaoMap link).

**Architecture:** Single-process Python app using `python-telegram-bot` long-polling (runs on the owner's PC, no public URL). A trigger phrase opens an in-memory "eat session"; members add cravings; a "Найти места" button runs a pipeline: Gemini extracts cravings → Korean queries, Kakao Local searches around a default-or-overridden area, Gemini ranks the results, and a formatter builds the Russian reply. The AI only selects/explains real Kakao results, so it cannot invent places. Logic lives in small, single-purpose modules; Telegram handlers are thin glue.

**Tech Stack:** Python 3.11+, python-telegram-bot 21, google-genai (Gemini 2.5 Flash), httpx (Kakao REST), python-dotenv, pytest + pytest-asyncio.

---

## File Structure

```
myo_mogille/
  bot.py                 # composition root: build app, register handlers, run polling
  foodbot/
    __init__.py
    config.py            # load + validate settings from .env -> Config
    dictionary.py        # craving Russian->Korean fallback map (LLM-down degraded mode)
    session.py           # trigger detection + in-memory session state machine
    places.py            # Place model, Kakao keyword search client, merge/dedup
    geo.py               # resolve a named area to coordinates (or default)
    llm.py               # provider-agnostic LLM: extract_cravings + rank_places (Gemini)
    formatting.py        # build the final Russian Telegram message
    pipeline.py          # orchestrate extract -> search -> rank -> format (+ degraded modes)
    handlers.py          # thin Telegram handlers wiring sessions + pipeline
  tests/
    __init__.py
    test_config.py
    test_dictionary.py
    test_session.py
    test_places.py
    test_geo.py
    test_llm.py
    test_formatting.py
    test_pipeline.py
    test_handlers.py
  requirements.txt
  requirements-dev.txt
  pytest.ini
  .gitignore
  .env.example
  README.md
  docs/superpowers/specs/2026-06-19-telegram-food-bot-design.md   # already committed
  docs/superpowers/plans/2026-06-19-telegram-food-bot.md          # this file
```

Each module has one responsibility and a small, explicit interface, so it can be tested in isolation with the function/clock/HTTP boundaries injected.

---

## Task 1: Project scaffolding & dependencies

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.gitignore`, `.env.example`, `foodbot/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```text
python-telegram-bot>=21.6,<22
google-genai>=1.0,<2
httpx>=0.26
python-dotenv>=1.0,<2
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```text
-r requirements.txt
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Create `.gitignore`**

```text
.env
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
.idea/
.vscode/
```

- [ ] **Step 5: Create `.env.example`**

```text
# Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN=
# Google AI Studio key (https://aistudio.google.com/apikey)
GEMINI_API_KEY=
# Kakao Developers REST API key (https://developers.kakao.com)
KAKAO_REST_API_KEY=
# Default search center (example below = Hongdae, Seoul)
DEFAULT_LAT=37.5563
DEFAULT_LNG=126.9220
DEFAULT_AREA_NAME=Hongdae
# Optional tuning (defaults shown)
SEARCH_RADIUS_M=1500
RESULTS_COUNT=3
SESSION_TIMEOUT_MIN=20
LLM_MODEL=gemini-2.5-flash
```

- [ ] **Step 6: Create empty package markers**

`foodbot/__init__.py`:
```python
```
`tests/__init__.py`:
```python
```

- [ ] **Step 7: Create venv and install dependencies**

Run (Windows PowerShell, from project root):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```
Expected: installs succeed.

- [ ] **Step 8: Verify the package imports**

Run: `python -c "import foodbot; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 9: Commit**

```powershell
git add requirements.txt requirements-dev.txt pytest.ini .gitignore .env.example foodbot/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure and dependencies"
```

---

## Task 2: Config loading (`foodbot/config.py`)

**Files:**
- Create: `foodbot/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
import pytest

from foodbot.config import load_config, Config, ConfigError, DEFAULT_TRIGGERS

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "tok",
    "GEMINI_API_KEY": "gem",
    "KAKAO_REST_API_KEY": "kak",
    "DEFAULT_LAT": "37.5",
    "DEFAULT_LNG": "127.0",
    "DEFAULT_AREA_NAME": "Hongdae",
}


def test_load_config_defaults():
    cfg = load_config(dict(BASE_ENV))
    assert isinstance(cfg, Config)
    assert cfg.telegram_bot_token == "tok"
    assert cfg.default_lat == 37.5
    assert cfg.default_lng == 127.0
    assert cfg.search_radius_m == 1500
    assert cfg.results_count == 3
    assert cfg.session_timeout_min == 20
    assert cfg.llm_model == "gemini-2.5-flash"
    assert cfg.trigger_phrases == DEFAULT_TRIGGERS


def test_load_config_overrides():
    env = dict(
        BASE_ENV,
        SEARCH_RADIUS_M="800",
        RESULTS_COUNT="5",
        TRIGGER_PHRASES="есть хочу, перекусим",
    )
    cfg = load_config(env)
    assert cfg.search_radius_m == 800
    assert cfg.results_count == 5
    assert cfg.trigger_phrases == ("есть хочу", "перекусим")


def test_load_config_missing_required():
    env = dict(BASE_ENV)
    del env["TELEGRAM_BOT_TOKEN"]
    with pytest.raises(ConfigError):
        load_config(env)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.config'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/config.py`:
```python
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_TRIGGERS: tuple[str, ...] = (
    "куда пойдем кушать",
    "куда пойдем поесть",
    "куда пойти поесть",
    "где поедим",
    "пойдем кушать",
    "пойдем есть",
)


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    gemini_api_key: str
    kakao_rest_api_key: str
    default_lat: float
    default_lng: float
    default_area_name: str
    search_radius_m: int = 1500
    results_count: int = 3
    session_timeout_min: int = 20
    llm_model: str = "gemini-2.5-flash"
    trigger_phrases: tuple[str, ...] = DEFAULT_TRIGGERS


def _require(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {key}")
    return value


def load_config(env: dict[str, str] | None = None) -> Config:
    """Build a Config. Pass an explicit env dict in tests; otherwise read .env + os.environ."""
    if env is None:
        load_dotenv()
        env = dict(os.environ)

    triggers_raw = env.get("TRIGGER_PHRASES", "").strip()
    if triggers_raw:
        triggers = tuple(p.strip().lower() for p in triggers_raw.split(",") if p.strip())
    else:
        triggers = DEFAULT_TRIGGERS

    return Config(
        telegram_bot_token=_require(env, "TELEGRAM_BOT_TOKEN"),
        gemini_api_key=_require(env, "GEMINI_API_KEY"),
        kakao_rest_api_key=_require(env, "KAKAO_REST_API_KEY"),
        default_lat=float(_require(env, "DEFAULT_LAT")),
        default_lng=float(_require(env, "DEFAULT_LNG")),
        default_area_name=_require(env, "DEFAULT_AREA_NAME"),
        search_radius_m=int(env.get("SEARCH_RADIUS_M", "1500")),
        results_count=int(env.get("RESULTS_COUNT", "3")),
        session_timeout_min=int(env.get("SESSION_TIMEOUT_MIN", "20")),
        llm_model=(env.get("LLM_MODEL", "").strip() or "gemini-2.5-flash"),
        trigger_phrases=triggers,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/config.py tests/test_config.py
git commit -m "feat: config loading with validation and defaults"
```

---

## Task 3: Dictionary fallback (`foodbot/dictionary.py`)

**Files:**
- Create: `foodbot/dictionary.py`
- Test: `tests/test_dictionary.py`

- [ ] **Step 1: Write the failing test**

`tests/test_dictionary.py`:
```python
from foodbot.dictionary import translate_cravings


def test_translate_known_words():
    assert translate_cravings("хочу соджу и кимчи") == ["소주", "김치찌개"]


def test_translate_dedup_and_unknown():
    assert translate_cravings("пиво, ещё пиво и непонятное слово") == ["맥주"]


def test_translate_nothing():
    assert translate_cravings("привет как дела") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dictionary.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.dictionary'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/dictionary.py`:
```python
from __future__ import annotations

# Lowercase Russian craving word -> Korean search query.
# Used only as a degraded fallback when the LLM is unavailable.
CRAVING_TO_KOREAN: dict[str, str] = {
    "соджу": "소주",
    "сочжу": "소주",
    "пиво": "맥주",
    "вино": "와인",
    "кимчи": "김치찌개",
    "мясо": "삼겹살",
    "самгёпсаль": "삼겹살",
    "барбекю": "고기",
    "суп": "찌개",
    "лапша": "국수",
    "рамён": "라멘",
    "рамен": "라멘",
    "суши": "스시",
    "пицца": "피자",
    "бургер": "햄버거",
    "чикен": "치킨",
    "курица": "치킨",
    "кофе": "카페",
    "десерт": "디저트",
    "сладкое": "디저트",
    "корейское": "한식",
}


def translate_cravings(text: str) -> list[str]:
    """Map recognized Russian craving words in `text` to Korean search queries.

    Returns a de-duplicated list preserving first-seen order.
    """
    lowered = text.lower()
    found: list[str] = []
    for word, korean in CRAVING_TO_KOREAN.items():
        if word in lowered and korean not in found:
            found.append(korean)
    return found
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dictionary.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/dictionary.py tests/test_dictionary.py
git commit -m "feat: Russian->Korean craving dictionary fallback"
```

---

## Task 4: Trigger detection + session store (`foodbot/session.py`)

**Files:**
- Create: `foodbot/session.py`
- Test: `tests/test_session.py`

- [ ] **Step 1: Write the failing test**

`tests/test_session.py`:
```python
from foodbot.config import DEFAULT_TRIGGERS
from foodbot.session import (
    is_trigger,
    normalize,
    Session,
    SessionStore,
    SessionState,
)


def test_normalize_lowercases_and_replaces_yo():
    assert normalize("ПойдЁм") == "пойдем"


def test_is_trigger_matches_variants():
    assert is_trigger("Ну что, куда пойдём кушать?", DEFAULT_TRIGGERS)
    assert is_trigger("ГДЕ ПОЕДИМ сегодня", DEFAULT_TRIGGERS)


def test_is_trigger_no_match():
    assert not is_trigger("сегодня хорошая погода", DEFAULT_TRIGGERS)


def test_session_store_lifecycle():
    clock = {"t": 100.0}
    store = SessionStore(timeout_min=20, now=lambda: clock["t"])
    assert store.get_active(1) is None

    session = store.start(1)
    assert session.state == SessionState.COLLECTING

    store.get_active(1).add_message("хочу соджу")
    store.get_active(1).add_message("   ")  # blank ignored
    assert store.get_active(1).messages == ["хочу соджу"]

    store.end(1)
    assert store.get_active(1) is None


def test_session_expiry():
    clock = {"t": 0.0}
    store = SessionStore(timeout_min=20, now=lambda: clock["t"])
    store.start(1)
    clock["t"] = 21 * 60  # 21 minutes later
    assert store.get_active(1) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_session.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.session'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/session.py`:
```python
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е").strip()


def is_trigger(text: str, phrases: tuple[str, ...]) -> bool:
    norm = normalize(text)
    return any(normalize(phrase) in norm for phrase in phrases)


class SessionState(Enum):
    IDLE = "idle"
    COLLECTING = "collecting"


@dataclass
class Session:
    chat_id: int
    state: SessionState = SessionState.IDLE
    messages: list[str] = field(default_factory=list)
    started_at: float = 0.0

    def add_message(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned:
            self.messages.append(cleaned)


class SessionStore:
    """In-memory per-chat sessions with lazy expiry."""

    def __init__(self, timeout_min: int, now: Callable[[], float] = time.monotonic) -> None:
        self._timeout_s = timeout_min * 60
        self._now = now
        self._sessions: dict[int, Session] = {}

    def start(self, chat_id: int) -> Session:
        session = Session(
            chat_id=chat_id,
            state=SessionState.COLLECTING,
            started_at=self._now(),
        )
        self._sessions[chat_id] = session
        return session

    def get_active(self, chat_id: int) -> Session | None:
        session = self._sessions.get(chat_id)
        if session is None or session.state != SessionState.COLLECTING:
            return None
        if self._now() - session.started_at > self._timeout_s:
            self.end(chat_id)
            return None
        return session

    def end(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_session.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/session.py tests/test_session.py
git commit -m "feat: trigger detection and in-memory session store"
```

---

## Task 5: Place model + Kakao client (`foodbot/places.py`)

**Files:**
- Create: `foodbot/places.py`
- Test: `tests/test_places.py`

- [ ] **Step 1: Write the failing test**

`tests/test_places.py`:
```python
import httpx

from foodbot.places import Place, parse_kakao_response, merge_places, KakaoClient

SAMPLE = {
    "documents": [
        {
            "id": "1",
            "place_name": "이자카야 하나",
            "category_name": "음식점 > 술집 > 이자카야",
            "road_address_name": "서울 마포구 와우산로",
            "address_name": "서울 마포구 서교동",
            "x": "126.9220",
            "y": "37.5563",
            "distance": "250",
            "place_url": "http://place.map.kakao.com/1",
            "phone": "02-111-1111",
        },
        {  # missing place_name -> skipped
            "id": "2",
            "place_name": "",
            "x": "126.9",
            "y": "37.5",
            "distance": "10",
            "place_url": "u",
        },
    ]
}


def test_parse_kakao_response():
    places = parse_kakao_response(SAMPLE)
    assert len(places) == 1
    p = places[0]
    assert p.name == "이자카야 하나"
    assert p.distance_m == 250
    assert p.lat == 37.5563
    assert p.lng == 126.9220
    assert p.url == "http://place.map.kakao.com/1"
    assert p.phone == "02-111-1111"


def test_merge_places_dedup_sort_cap():
    a = Place("1", "A", "c", "addr", 37.5, 127.0, 300, "u")
    b = Place("2", "B", "c", "addr", 37.5, 127.0, 100, "u")
    dup = Place("1", "A", "c", "addr", 37.5, 127.0, 300, "u")
    merged = merge_places([[a, b], [dup]], cap=10)
    assert [p.id for p in merged] == ["2", "1"]


async def test_kakao_search_builds_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=SAMPLE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    kakao = KakaoClient("MYKEY", client=client)
    places = await kakao.search("소주", 37.5563, 126.9220, 1500)
    await kakao.aclose()

    assert places[0].name == "이자카야 하나"
    assert "query=" in captured["url"]
    assert "radius=1500" in captured["url"]
    assert captured["auth"] == "KakaoAK MYKEY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_places.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.places'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/places.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

import httpx

KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    category: str
    address: str
    lat: float
    lng: float
    distance_m: int
    url: str
    phone: str = ""


def parse_kakao_response(payload: dict) -> list[Place]:
    places: list[Place] = []
    for doc in payload.get("documents", []):
        try:
            place = Place(
                id=str(doc.get("id", "")),
                name=doc.get("place_name", "") or "",
                category=doc.get("category_name", "") or "",
                address=doc.get("road_address_name") or doc.get("address_name", "") or "",
                lat=float(doc.get("y", 0.0)),
                lng=float(doc.get("x", 0.0)),
                distance_m=int(doc.get("distance") or 0),
                url=doc.get("place_url", "") or "",
                phone=doc.get("phone", "") or "",
            )
        except (TypeError, ValueError):
            continue
        if place.name:
            places.append(place)
    return places


def merge_places(results: list[list[Place]], cap: int = 20) -> list[Place]:
    seen: set[str] = set()
    merged: list[Place] = []
    for group in results:
        for place in group:
            key = place.id or place.name
            if key in seen:
                continue
            seen.add(key)
            merged.append(place)
    merged.sort(key=lambda p: p.distance_m)
    return merged[:cap]


class KakaoClient:
    def __init__(self, rest_api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = rest_api_key
        self._client = client or httpx.AsyncClient(timeout=10.0)

    async def search(
        self, query: str, lat: float, lng: float, radius_m: int, size: int = 15
    ) -> list[Place]:
        resp = await self._client.get(
            KAKAO_KEYWORD_URL,
            headers={"Authorization": f"KakaoAK {self._key}"},
            params={
                "query": query,
                "x": str(lng),
                "y": str(lat),
                "radius": str(radius_m),
                "sort": "distance",
                "size": str(size),
            },
        )
        resp.raise_for_status()
        return parse_kakao_response(resp.json())

    async def geocode(self, query: str) -> tuple[float, float] | None:
        """Resolve a place/area name to (lat, lng) via nationwide keyword search."""
        resp = await self._client.get(
            KAKAO_KEYWORD_URL,
            headers={"Authorization": f"KakaoAK {self._key}"},
            params={"query": query, "size": "1"},
        )
        resp.raise_for_status()
        places = parse_kakao_response(resp.json())
        if not places:
            return None
        return (places[0].lat, places[0].lng)

    async def aclose(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_places.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/places.py tests/test_places.py
git commit -m "feat: Place model and Kakao keyword search client"
```

---

## Task 6: Area resolution (`foodbot/geo.py`)

**Files:**
- Create: `foodbot/geo.py`
- Test: `tests/test_geo.py`

- [ ] **Step 1: Write the failing test**

`tests/test_geo.py`:
```python
from foodbot.geo import GeoPoint, resolve_area

DEFAULT = GeoPoint(37.5, 127.0, "Home")


class FakeKakao:
    def __init__(self, coords):
        self._coords = coords

    async def geocode(self, query):
        return self._coords


async def test_resolve_area_found():
    point = await resolve_area(FakeKakao((37.55, 126.92)), "홍대", DEFAULT)
    assert point == GeoPoint(37.55, 126.92, "홍대")


async def test_resolve_area_not_found_falls_back():
    point = await resolve_area(FakeKakao(None), "несуществующее", DEFAULT)
    assert point == DEFAULT


async def test_resolve_area_empty_falls_back():
    point = await resolve_area(FakeKakao((1.0, 2.0)), "", DEFAULT)
    assert point == DEFAULT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_geo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.geo'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/geo.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lng: float
    label: str


class _Geocoder(Protocol):
    async def geocode(self, query: str) -> tuple[float, float] | None: ...


async def resolve_area(kakao: _Geocoder, area: str, default: GeoPoint) -> GeoPoint:
    """Resolve a neighborhood name to a GeoPoint, falling back to `default`."""
    area = (area or "").strip()
    if not area:
        return default
    coords = await kakao.geocode(area)
    if coords is None:
        return default
    return GeoPoint(lat=coords[0], lng=coords[1], label=area)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_geo.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/geo.py tests/test_geo.py
git commit -m "feat: resolve named area to coordinates via Kakao"
```

---

## Task 7: LLM wrapper (`foodbot/llm.py`)

**Files:**
- Create: `foodbot/llm.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: Write the failing test**

`tests/test_llm.py`:
```python
from foodbot.llm import (
    CravingResult,
    Pick,
    parse_extract,
    parse_ranking,
    GeminiLLM,
)
from foodbot.places import Place


def test_parse_extract_plain_json():
    raw = '{"cravings":["soju"],"search_queries":["소주"],"area":"홍대","no_preference":false}'
    result = parse_extract(raw)
    assert result.search_queries == ["소주"]
    assert result.area == "홍대"
    assert result.no_preference is False


def test_parse_extract_code_fenced():
    raw = '```json\n{"cravings":[],"search_queries":[],"area":null,"no_preference":true}\n```'
    result = parse_extract(raw)
    assert result.no_preference is True
    assert result.area is None


def test_parse_ranking_filters_bad_index():
    raw = '{"picks":[{"index":0,"reason_ru":"ок"},{"index":9,"reason_ru":"нет"}]}'
    picks = parse_ranking(raw, max_index=1)
    assert len(picks) == 1
    assert picks[0] == Pick(0, "ок")


class StubLLM(GeminiLLM):
    """Bypass the real SDK: override __init__ and _generate."""

    def __init__(self, canned: str):
        self._canned = canned
        self._model = "stub"
        self.last_user = None

    def _generate(self, system: str, user: str) -> str:
        self.last_user = user
        return self._canned


async def test_extract_cravings_calls_generate():
    stub = StubLLM('{"cravings":["soju"],"search_queries":["소주"],"area":null,"no_preference":false}')
    result = await stub.extract_cravings(["хочу соджу"])
    assert isinstance(result, CravingResult)
    assert result.search_queries == ["소주"]
    assert "соджу" in stub.last_user


async def test_rank_places_calls_generate():
    stub = StubLLM('{"picks":[{"index":0,"reason_ru":"соджу"}]}')
    places = [Place("1", "A", "술집", "addr", 37.5, 127.0, 100, "u")]
    picks = await stub.rank_places(["소주"], places, 3)
    assert picks == [Pick(0, "соджу")]
    assert "A" in stub.last_user
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.llm'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/llm.py`:
```python
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from foodbot.places import Place


@dataclass
class CravingResult:
    cravings: list[str]
    search_queries: list[str]
    area: str | None
    no_preference: bool


@dataclass
class Pick:
    index: int
    reason_ru: str


EXTRACT_SYSTEM = (
    "Ты помощник, который читает переписку друзей (на русском) о том, что они хотят "
    "поесть или выпить, и превращает её в поисковые запросы для корейских карт.\n"
    "Верни СТРОГО JSON по схеме:\n"
    '{"cravings": [строки], "search_queries": [корейские строки], '
    '"area": строка или null, "no_preference": булево}\n'
    "- search_queries — короткие корейские слова для поиска заведений "
    "(например соджу → 이자카야 или 소주, кимчи → 김치찌개, мясо → 삼겹살).\n"
    "- area — район, если кто-то его назвал (например «Хондэ» → «홍대»), иначе null.\n"
    "- no_preference=true, если никто не написал ни одного пожелания о еде или напитках.\n"
    "Ответь только JSON, без пояснений."
)

RANK_SYSTEM = (
    "Ты выбираешь из списка заведений лучшие, которые покрывают пожелания группы.\n"
    "Тебе дают cravings (что хотят) и пронумерованный список мест "
    "(index, name, category, distance).\n"
    'Верни СТРОГО JSON: {"picks": [{"index": число, "reason_ru": "короткое объяснение по-русски"}]}\n'
    "- Выбери до N лучших мест, по возможности покрывая разные пожелания.\n"
    "- reason_ru — одна короткая фраза, почему место подходит (можно с эмодзи).\n"
    "- Используй только индексы из данного списка. Ответь только JSON."
)


def _strip_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text


def parse_extract(raw: str) -> CravingResult:
    data = json.loads(_strip_json(raw))
    return CravingResult(
        cravings=list(data.get("cravings", [])),
        search_queries=list(data.get("search_queries", [])),
        area=data.get("area") or None,
        no_preference=bool(data.get("no_preference", False)),
    )


def parse_ranking(raw: str, max_index: int) -> list[Pick]:
    data = json.loads(_strip_json(raw))
    picks: list[Pick] = []
    for item in data.get("picks", []):
        idx = item.get("index")
        if isinstance(idx, int) and 0 <= idx <= max_index:
            picks.append(Pick(index=idx, reason_ru=str(item.get("reason_ru", "")).strip()))
    return picks


class GeminiLLM:
    """Provider-agnostic surface backed by Gemini. Swap by replacing this class."""

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client

    def _generate(self, system: str, user: str) -> str:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        return response.text or ""

    async def extract_cravings(self, messages: list[str]) -> CravingResult:
        user = "Сообщения группы:\n" + "\n".join(f"- {m}" for m in messages)
        raw = await asyncio.to_thread(self._generate, EXTRACT_SYSTEM, user)
        return parse_extract(raw)

    async def rank_places(self, cravings: list[str], places: list[Place], count: int) -> list[Pick]:
        lines = [
            f"{i}. {p.name} | {p.category} | {p.distance_m}м"
            for i, p in enumerate(places)
        ]
        user = (
            f"cravings: {', '.join(cravings)}\n"
            f"N = {count}\n"
            "Места:\n" + "\n".join(lines)
        )
        raw = await asyncio.to_thread(self._generate, RANK_SYSTEM, user)
        return parse_ranking(raw, max_index=len(places) - 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_llm.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/llm.py tests/test_llm.py
git commit -m "feat: Gemini-backed LLM wrapper for extract and rank"
```

---

## Task 8: Message formatting (`foodbot/formatting.py`)

**Files:**
- Create: `foodbot/formatting.py`
- Test: `tests/test_formatting.py`

- [ ] **Step 1: Write the failing test**

`tests/test_formatting.py`:
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
    assert "http://map/1" in msg
    assert "соджу + закуски" in msg
    assert msg.count("http://map/") == 2


def test_build_message_empty():
    msg = build_message("홍대", PLACES, [])
    assert "Ничего" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_formatting.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.formatting'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/formatting.py`:
```python
from __future__ import annotations

from foodbot.places import Place
from foodbot.llm import Pick


def build_message(area_label: str, places: list[Place], picks: list[Pick]) -> str:
    """Plain-text Russian message (no Markdown -> no escaping pitfalls).

    Telegram auto-links the bare URLs.
    """
    if not picks:
        return "Ничего подходящего не нашёл 😕 Попробуйте другие пожелания или район."

    header = f"Нашёл {len(picks)} мест рядом (район: {area_label}) 👇"
    blocks: list[str] = []
    for number, pick in enumerate(picks, start=1):
        place = places[pick.index]
        reason = pick.reason_ru or place.category
        distance = f"{place.distance_m} м" if place.distance_m else ""
        head = f"{number}. {place.name} ({place.category})"
        if distance:
            head += f" — {distance}"
        blocks.append(f"{head}\n{reason}\n{place.url}")

    return header + "\n\n" + "\n\n".join(blocks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_formatting.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/formatting.py tests/test_formatting.py
git commit -m "feat: build Russian reply message from places and picks"
```

---

## Task 9: Pipeline orchestration (`foodbot/pipeline.py`)

**Files:**
- Create: `foodbot/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

`tests/test_pipeline.py`:
```python
from foodbot.geo import GeoPoint
from foodbot.places import Place
from foodbot.llm import CravingResult, Pick
from foodbot import pipeline

DEFAULT = GeoPoint(37.5, 127.0, "Home")
P1 = Place("1", "이자카야", "술집", "addr", 37.5, 127.0, 250, "http://m/1")


class FakeKakao:
    def __init__(self, by_query, coords=None):
        self.by_query = by_query
        self._coords = coords

    async def search(self, query, lat, lng, radius_m, size=15):
        return list(self.by_query.get(query, []))

    async def geocode(self, query):
        return self._coords


class FakeLLM:
    def __init__(self, extract=None, picks=None, fail_extract=False, fail_rank=False):
        self._extract = extract
        self._picks = picks or []
        self._fail_extract = fail_extract
        self._fail_rank = fail_rank

    async def extract_cravings(self, messages):
        if self._fail_extract:
            raise RuntimeError("llm down")
        return self._extract

    async def rank_places(self, cravings, places, count):
        if self._fail_rank:
            raise RuntimeError("llm down")
        return self._picks


def _deps(llm, kakao, results_count=3):
    return pipeline.PipelineDeps(
        llm=llm,
        kakao=kakao,
        default_point=DEFAULT,
        radius_m=1500,
        results_count=results_count,
    )


async def test_pipeline_happy_path():
    llm = FakeLLM(
        extract=CravingResult(["soju"], ["소주"], None, False),
        picks=[Pick(0, "соджу")],
    )
    kakao = FakeKakao({"소주": [P1]})
    msg = await pipeline.run(["хочу соджу"], _deps(llm, kakao))
    assert "이자카야" in msg
    assert "соджу" in msg


async def test_pipeline_no_preference_nudges():
    llm = FakeLLM(extract=CravingResult([], [], None, True))
    msg = await pipeline.run(["привет"], _deps(llm, FakeKakao({})))
    assert "Я не понял" in msg


async def test_pipeline_no_results():
    llm = FakeLLM(extract=CravingResult(["soju"], ["소주"], None, False))
    msg = await pipeline.run(["соджу"], _deps(llm, FakeKakao({})))
    assert "Ничего не нашёл" in msg


async def test_pipeline_extract_failure_uses_dictionary():
    llm = FakeLLM(fail_extract=True, picks=[Pick(0, "")])
    kakao = FakeKakao({"소주": [P1]})  # dictionary maps соджу -> 소주
    msg = await pipeline.run(["хочу соджу"], _deps(llm, kakao))
    assert "이자카야" in msg


async def test_pipeline_rank_failure_uses_nearest():
    llm = FakeLLM(
        extract=CravingResult(["soju"], ["소주"], None, False),
        fail_rank=True,
    )
    kakao = FakeKakao({"소주": [P1]})
    msg = await pipeline.run(["соджу"], _deps(llm, kakao))
    assert "이자카야" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.pipeline'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/pipeline.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from foodbot import dictionary
from foodbot.formatting import build_message
from foodbot.geo import GeoPoint, resolve_area
from foodbot.llm import Pick
from foodbot.places import merge_places

NUDGE = (
    "Я не понял, что вы хотите 🤔 Напишите, что хотите поесть или выпить "
    "(например: соджу, кимчи, мясо), потом жмите кнопку."
)
NOT_FOUND = "Ничего не нашёл рядом 😕 Попробуйте другой район или другие пожелания."


@dataclass
class PipelineDeps:
    llm: Any                # has extract_cravings(messages) / rank_places(cravings, places, count)
    kakao: Any              # has search(query, lat, lng, radius_m, size) / geocode(query)
    default_point: GeoPoint
    radius_m: int
    results_count: int


async def _search_all(kakao: Any, queries: list[str], point: GeoPoint, radius_m: int) -> list:
    groups: list[list] = []
    for query in queries:
        try:
            groups.append(await kakao.search(query, point.lat, point.lng, radius_m))
        except Exception:
            continue
    return merge_places(groups)


async def run(messages: list[str], deps: PipelineDeps) -> str:
    # 1. Understand cravings (LLM), with dictionary fallback if the LLM is down.
    area: str | None = None
    try:
        extract = await deps.llm.extract_cravings(messages)
        queries = list(extract.search_queries)
        area = extract.area
        no_preference = extract.no_preference
    except Exception:
        queries = dictionary.translate_cravings(" ".join(messages))
        no_preference = not queries

    if no_preference or not queries:
        return NUDGE

    # 2. Resolve search center.
    point = deps.default_point
    if area:
        try:
            point = await resolve_area(deps.kakao, area, deps.default_point)
        except Exception:
            point = deps.default_point

    # 3. Search (widen radius once if nothing nearby).
    results = await _search_all(deps.kakao, queries, point, deps.radius_m)
    if not results:
        results = await _search_all(deps.kakao, queries, point, deps.radius_m * 2)
    if not results:
        return NOT_FOUND

    # 4. Rank (LLM), with nearest-first fallback if the LLM is down.
    try:
        picks = await deps.llm.rank_places(queries, results, deps.results_count)
    except Exception:
        picks = []
    if not picks:
        picks = [
            Pick(index=i, reason_ru=results[i].category)
            for i in range(min(deps.results_count, len(results)))
        ]

    # 5. Format.
    return build_message(point.label, results, picks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add foodbot/pipeline.py tests/test_pipeline.py
git commit -m "feat: orchestration pipeline with degraded-mode fallbacks"
```

---

## Task 10: Telegram handlers (`foodbot/handlers.py`)

**Files:**
- Create: `foodbot/handlers.py`
- Test: `tests/test_handlers.py`

- [ ] **Step 1: Write the failing test**

`tests/test_handlers.py`:
```python
from unittest.mock import AsyncMock, MagicMock

from foodbot.config import load_config
from foodbot.session import SessionStore
from foodbot import handlers, pipeline

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "t",
    "GEMINI_API_KEY": "g",
    "KAKAO_REST_API_KEY": "k",
    "DEFAULT_LAT": "37.5",
    "DEFAULT_LNG": "127.0",
    "DEFAULT_AREA_NAME": "Home",
}


def _context():
    ctx = MagicMock()
    ctx.application.bot_data = {
        "config": load_config(dict(BASE_ENV)),
        "sessions": SessionStore(timeout_min=20),
        "llm": object(),
        "kakao": object(),
        "default_point": object(),
    }
    ctx.bot.send_message = AsyncMock()
    return ctx


def _update(chat_id, text=None, callback=False):
    upd = MagicMock()
    upd.effective_chat.id = chat_id
    msg = MagicMock()
    msg.text = text
    msg.reply_text = AsyncMock()
    upd.effective_message = msg
    if callback:
        upd.callback_query = MagicMock()
        upd.callback_query.answer = AsyncMock()
    else:
        upd.callback_query = None
    return upd, msg


def _sent_texts(ctx):
    return [c.kwargs.get("text") for c in ctx.bot.send_message.await_args_list]


async def test_on_text_starts_session_on_trigger():
    ctx = _context()
    upd, msg = _update(1, "куда пойдём кушать?")
    await handlers.on_text(upd, ctx)
    assert ctx.application.bot_data["sessions"].get_active(1) is not None
    msg.reply_text.assert_awaited()


async def test_on_text_collects_messages():
    ctx = _context()
    ctx.application.bot_data["sessions"].start(1)
    upd, _ = _update(1, "хочу соджу")
    await handlers.on_text(upd, ctx)
    session = ctx.application.bot_data["sessions"].get_active(1)
    assert session.messages == ["хочу соджу"]


async def test_on_go_without_session():
    ctx = _context()
    upd, _ = _update(1, callback=True)
    await handlers.on_go(upd, ctx)
    assert any("Сессия" in (t or "") for t in _sent_texts(ctx))


async def test_on_go_runs_pipeline(monkeypatch):
    ctx = _context()
    store = ctx.application.bot_data["sessions"]
    store.start(1)
    store.get_active(1).add_message("хочу соджу")

    async def fake_run(messages, deps):
        return "РЕЗУЛЬТАТ"

    monkeypatch.setattr(pipeline, "run", fake_run)
    upd, _ = _update(1, callback=True)
    await handlers.on_go(upd, ctx)

    assert store.get_active(1) is None  # session ended
    assert any("РЕЗУЛЬТАТ" in (t or "") for t in _sent_texts(ctx))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'foodbot.handlers'`.

- [ ] **Step 3: Write minimal implementation**

`foodbot/handlers.py`:
```python
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from foodbot import pipeline
from foodbot.geo import GeoPoint
from foodbot.session import is_trigger

logger = logging.getLogger(__name__)

START_PROMPT = (
    "Окей, собираю пожелания! 🍽 Пишите, что хотите — соджу, кимчи, мясо… "
    "Можно указать район (например «в Хондэ»). Когда готовы — жмите кнопку."
)
FIND_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🍽 Найти места", callback_data="find")]]
)
NO_SESSION = "Сессия истекла или не начата. Напишите «куда пойдём кушать?» заново."
NO_MESSAGES = "Пока никто не написал пожеланий 🤔 Напишите, что хотите, потом жмите кнопку."
SEARCHING = "Секунду, ищу подходящие места… 🔎"
ERROR = "Упс, что-то пошло не так. Попробуйте ещё раз чуть позже."


def _build_deps(context: ContextTypes.DEFAULT_TYPE) -> pipeline.PipelineDeps:
    bot_data = context.application.bot_data
    config = bot_data["config"]
    return pipeline.PipelineDeps(
        llm=bot_data["llm"],
        kakao=bot_data["kakao"],
        default_point=bot_data["default_point"],
        radius_m=config.search_radius_m,
        results_count=config.results_count,
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    chat_id = update.effective_chat.id
    config = context.application.bot_data["config"]
    sessions = context.application.bot_data["sessions"]

    if is_trigger(message.text, config.trigger_phrases):
        sessions.start(chat_id)
        await message.reply_text(START_PROMPT, reply_markup=FIND_BUTTON)
        return

    session = sessions.get_active(chat_id)
    if session is not None:
        session.add_message(message.text)


async def on_eat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    context.application.bot_data["sessions"].start(chat_id)
    await context.bot.send_message(chat_id=chat_id, text=START_PROMPT, reply_markup=FIND_BUTTON)


async def on_go(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query is not None:
        await update.callback_query.answer()
    chat_id = update.effective_chat.id
    sessions = context.application.bot_data["sessions"]
    session = sessions.get_active(chat_id)

    if session is None:
        await context.bot.send_message(chat_id=chat_id, text=NO_SESSION)
        return
    if not session.messages:
        await context.bot.send_message(chat_id=chat_id, text=NO_MESSAGES)
        return

    messages = list(session.messages)
    sessions.end(chat_id)
    await context.bot.send_message(chat_id=chat_id, text=SEARCHING)
    try:
        reply = await pipeline.run(messages, _build_deps(context))
    except Exception:
        logger.exception("pipeline failed")
        reply = ERROR
    await context.bot.send_message(chat_id=chat_id, text=reply)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests pass (config 3, dictionary 3, session 5, places 3, geo 3, llm 5, formatting 2, pipeline 5, handlers 4).

- [ ] **Step 6: Commit**

```powershell
git add foodbot/handlers.py tests/test_handlers.py
git commit -m "feat: Telegram handlers for trigger, collect, and find"
```

---

## Task 11: Composition root (`bot.py`)

**Files:**
- Create: `bot.py`

This is the wiring/entry point. It is not unit-tested (it only composes already-tested
parts and starts the network loop); it is verified by an import smoke check and a manual run.

- [ ] **Step 1: Write `bot.py`**

```python
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from foodbot import handlers
from foodbot.config import load_config
from foodbot.geo import GeoPoint
from foodbot.llm import GeminiLLM
from foodbot.places import KakaoClient
from foodbot.session import SessionStore


def build_application() -> Application:
    config = load_config()
    app = Application.builder().token(config.telegram_bot_token).build()

    app.bot_data["config"] = config
    app.bot_data["sessions"] = SessionStore(timeout_min=config.session_timeout_min)
    app.bot_data["kakao"] = KakaoClient(config.kakao_rest_api_key)
    app.bot_data["llm"] = GeminiLLM(api_key=config.gemini_api_key, model=config.llm_model)
    app.bot_data["default_point"] = GeoPoint(
        config.default_lat, config.default_lng, config.default_area_name
    )

    app.add_handler(CommandHandler("eat", handlers.on_eat))
    app.add_handler(CommandHandler("go", handlers.on_go))
    app.add_handler(CallbackQueryHandler(handlers.on_go, pattern="^find$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text))
    return app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = build_application()
    logging.getLogger(__name__).info("Bot starting (long polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-check that the module imports**

Run: `python -c "import bot; print('ok')"`
Expected: prints `ok` (no network call; `build_application` is not invoked on import).

- [ ] **Step 3: Manual run check (requires a filled `.env`)**

Copy `.env.example` to `.env` and fill in the three keys + default coordinates, then run:
```powershell
python bot.py
```
Expected: logs "Bot starting (long polling)…" and no crash. Stop with Ctrl+C.
(If `.env` is not yet filled, skip this step until Task 12's setup is done.)

- [ ] **Step 4: Commit**

```powershell
git add bot.py
git commit -m "feat: bot entry point wiring handlers and polling"
```

---

## Task 12: README & setup documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# куда пойдём 🍽 — Telegram food-decider bot

A Telegram group-chat bot. When someone asks **«куда пойдём кушать?»**, it collects
everyone's cravings, then suggests ~3 nearby Korean restaurants with KakaoMap links.

## How it works
1. Someone sends a trigger phrase (e.g. «куда пойдём кушать?») or `/eat`.
2. The bot opens a collection session and shows a **🍽 Найти места** button.
3. Everyone types what they want (соджу, кимчи, мясо…). Optionally name a district
   (e.g. «в Хондэ»).
4. Anyone taps the button (or sends `/go`).
5. The bot replies with matched places — name, type, distance, and a KakaoMap link.

## Setup

### 1. Telegram bot
- You already have a token from [@BotFather](https://t.me/BotFather).
- **Disable privacy mode** so the bot can read group messages:
  BotFather → `/setprivacy` → select your bot → **Disable**.
  (Without this the bot only sees commands, not cravings.)
- Add the bot to your group.

### 2. API keys (both free)
- **Kakao REST key:** https://developers.kakao.com → create an app → REST API key.
- **Gemini key:** https://aistudio.google.com/apikey

### 3. Configure
```powershell
copy .env.example .env
```
Fill in `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `KAKAO_REST_API_KEY`, and
`DEFAULT_LAT` / `DEFAULT_LNG` / `DEFAULT_AREA_NAME` (your usual area; the example
values point at Hongdae, Seoul).

### 4. Install & run
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bot.py
```
The bot runs on your PC via long-polling — it's online while this process runs.

## Development
```powershell
pip install -r requirements-dev.txt
python -m pytest -v
```

## Configuration reference
| Variable | Meaning | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather token | required |
| `GEMINI_API_KEY` | Google AI Studio key | required |
| `KAKAO_REST_API_KEY` | Kakao Developers REST key | required |
| `DEFAULT_LAT` / `DEFAULT_LNG` | Default search center | required |
| `DEFAULT_AREA_NAME` | Label for the default area | required |
| `SEARCH_RADIUS_M` | Search radius (meters) | 1500 |
| `RESULTS_COUNT` | Places returned | 3 |
| `SESSION_TIMEOUT_MIN` | Collection window | 20 |
| `LLM_MODEL` | Gemini model id | gemini-2.5-flash |
| `TRIGGER_PHRASES` | Comma-separated override | built-in list |
````

- [ ] **Step 2: Verify the full suite still passes**

Run: `python -m pytest -v`
Expected: all tests pass.

- [ ] **Step 3: Commit**

```powershell
git add README.md
git commit -m "docs: setup and usage README"
```

---

## Self-Review (completed during planning)

**Spec coverage** — every spec section maps to a task:
- Trigger → collect → button flow → Tasks 4, 10, 11.
- Default-area-with-named-override → Tasks 6, 9 (pin override is post-MVP, per spec).
- AI understanding (extract) + ranking, provider-agnostic, JSON → Task 7.
- Kakao Local place search (fields, radius, sort, dedup) → Task 5.
- Russian, map-link-only output → Task 8.
- In-memory sessions + lazy expiry → Task 4.
- Error/degraded modes (no-preference nudge, dictionary fallback on LLM failure,
  widen-radius then not-found, nearest-first ranking fallback) → Tasks 3, 9.
- Config via `.env` with all documented keys → Task 2.
- Long-polling on PC, setup incl. BotFather privacy mode → Tasks 11, 12.
- Testing strategy (pure units + mocked HTTP/SDK + pipeline + handlers) → Tasks 2–10.

**Placeholder scan** — no TBD/TODO; every code step contains complete code.

**Type consistency** — verified across tasks: `Place(id,name,category,address,lat,lng,distance_m,url,phone)`,
`Pick(index,reason_ru)`, `CravingResult(cravings,search_queries,area,no_preference)`,
`GeoPoint(lat,lng,label)`, `KakaoClient.search(query,lat,lng,radius_m,size)` / `.geocode(query)`,
`SessionStore(timeout_min,now)` / `.start/.get_active/.end`,
`PipelineDeps(llm,kakao,default_point,radius_m,results_count)` / `pipeline.run(messages,deps)`,
`build_message(area_label,places,picks)`. All call sites match their definitions.
````
