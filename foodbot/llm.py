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
