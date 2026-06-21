from __future__ import annotations

from dataclasses import dataclass
import logging
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
SEARCH_ERROR = "Сейчас временно не могу проверить места 😕 Попробуйте ещё раз чуть позже."

logger = logging.getLogger(__name__)


@dataclass
class PipelineDeps:
    llm: Any                # has extract_cravings(messages) / rank_places(cravings, places, count)
    kakao: Any              # has search(query, lat, lng, radius_m, size) / geocode(query)
    default_point: GeoPoint
    radius_m: int
    results_count: int


@dataclass
class SearchBatch:
    places: list
    failures: int


async def _search_all(kakao: Any, queries: list[str], point: GeoPoint, radius_m: int) -> SearchBatch:
    groups: list[list] = []
    failures = 0
    for query in queries:
        try:
            groups.append(await kakao.search(query, point.lat, point.lng, radius_m))
        except Exception as exc:
            failures += 1
            logger.warning(
                "Kakao search failed for query=%r lat=%s lng=%s radius_m=%s: %s",
                query,
                point.lat,
                point.lng,
                radius_m,
                exc.__class__.__name__,
            )
            continue
    return SearchBatch(places=merge_places(groups), failures=failures)


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
    first_search = await _search_all(deps.kakao, queries, point, deps.radius_m)
    results = first_search.places
    search_failures = first_search.failures
    if not results:
        second_search = await _search_all(deps.kakao, queries, point, deps.radius_m * 2)
        results = second_search.places
        search_failures += second_search.failures
    if not results:
        if search_failures:
            return SEARCH_ERROR
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
