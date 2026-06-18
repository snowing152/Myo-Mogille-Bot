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
