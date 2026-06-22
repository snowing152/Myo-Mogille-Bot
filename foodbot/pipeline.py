from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from foodbot import dictionary
from foodbot.evidence import BlogEvidence, collect_blog_evidence
from foodbot.formatting import build_message
from foodbot.geo import GeoPoint, resolve_area
from foodbot.llm import Pick
from foodbot.places import merge_places
from foodbot.search_queries import expand_search_queries

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
    naver: Any | None = None
    naver_blog_evidence_enabled: bool = False
    naver_blog_evidence_limit: int = 3


@dataclass
class SearchBatch:
    places: list
    evidence: dict[str, "SearchEvidence"]
    failures: int


@dataclass
class SearchEvidence:
    queries: list[str]
    best_rank: int
    first_radius_m: int


def _place_key(place: Any) -> str:
    return place.id or place.name


def _record_search_evidence(
    evidence: dict[str, SearchEvidence],
    place: Any,
    query: str,
    rank: int,
    radius_m: int,
) -> None:
    key = _place_key(place)
    current = evidence.get(key)
    if current is None:
        evidence[key] = SearchEvidence(queries=[query], best_rank=rank, first_radius_m=radius_m)
        return
    if query not in current.queries:
        current.queries.append(query)
    current.best_rank = min(current.best_rank, rank)
    current.first_radius_m = min(current.first_radius_m, radius_m)


def _score_place(
    place: Any,
    search_evidence: dict[str, SearchEvidence],
    blog_evidence: dict[str, BlogEvidence],
    queries: list[str],
) -> float:
    key = _place_key(place)
    evidence = search_evidence.get(key)
    score = max(0.0, 20.0 - (place.distance_m / 100.0))
    text = f"{place.name} {place.category}"
    if evidence is not None:
        score += len(evidence.queries) * 20
        score += max(0, 16 - evidence.best_rank * 2)
        score += sum(8 for query in evidence.queries if query and query in text)
    score += sum(12 for query in queries if query and query in text)

    blogs = blog_evidence.get(key)
    if blogs is not None:
        score += len(blogs.matched_terms) * 14
        score += sum(8 for query in queries if query in blogs.matched_terms)
        score += len(blogs.prices) * 3
        score += len(blogs.hints) * 2
    return score


def _rank_candidates(
    places: list[Any],
    search_evidence: dict[str, SearchEvidence],
    blog_evidence: dict[str, BlogEvidence],
    queries: list[str],
) -> list[Any]:
    return sorted(
        places,
        key=lambda place: (
            -_score_place(place, search_evidence, blog_evidence, queries),
            place.distance_m,
            place.name,
        ),
    )


def _ranking_evidence_lines(
    places: list[Any],
    search_evidence: dict[str, SearchEvidence],
    blog_evidence: dict[str, BlogEvidence],
) -> list[str]:
    lines: list[str] = []
    for place in places:
        key = _place_key(place)
        parts: list[str] = []
        evidence = search_evidence.get(key)
        if evidence is not None:
            parts.append(
                "kakao_queries="
                + ", ".join(evidence.queries)
                + f"; best_kakao_rank={evidence.best_rank}"
            )
        blogs = blog_evidence.get(key)
        if blogs is not None:
            if blogs.matched_terms:
                parts.append("blog_terms=" + ", ".join(blogs.matched_terms[:6]))
            if blogs.prices:
                parts.append("blog_prices=" + ", ".join(blogs.prices[:3]))
            if blogs.hints:
                parts.append("blog_hints=" + ", ".join(blogs.hints[:4]))
        lines.append("; ".join(parts))
    return lines


async def _search_all(kakao: Any, queries: list[str], point: GeoPoint, radius_m: int) -> SearchBatch:
    groups: list[list] = []
    evidence: dict[str, SearchEvidence] = {}
    failures = 0
    for query in queries:
        try:
            places = await kakao.search(query, point.lat, point.lng, radius_m)
            groups.append(places)
            for rank, place in enumerate(places, start=1):
                _record_search_evidence(evidence, place, query, rank, radius_m)
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
    return SearchBatch(places=merge_places(groups), evidence=evidence, failures=failures)


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
    search_queries = expand_search_queries(queries)
    first_search = await _search_all(deps.kakao, search_queries, point, deps.radius_m)
    results = first_search.places
    search_evidence = first_search.evidence
    search_failures = first_search.failures
    if not results:
        second_search = await _search_all(deps.kakao, search_queries, point, deps.radius_m * 2)
        results = second_search.places
        search_evidence = second_search.evidence
        search_failures += second_search.failures
    if not results:
        if search_failures:
            return SEARCH_ERROR
        return NOT_FOUND

    blog_evidence: dict[str, BlogEvidence] = {}
    if deps.naver is not None and deps.naver_blog_evidence_enabled:
        try:
            blog_evidence = await collect_blog_evidence(
                deps.naver,
                results[:10],
                point.label,
                queries,
                limit=deps.naver_blog_evidence_limit,
            )
        except Exception as exc:
            logger.warning("Naver blog evidence failed: %s", exc.__class__.__name__)
            blog_evidence = {}
    results = _rank_candidates(results, search_evidence, blog_evidence, queries)

    # 4. Rank (LLM), with nearest-first fallback if the LLM is down.
    try:
        picks = await deps.llm.rank_places(
            queries,
            results,
            deps.results_count,
            evidence_lines=_ranking_evidence_lines(results, search_evidence, blog_evidence),
        )
    except Exception:
        picks = []
    if not picks:
        picks = [
            Pick(index=i, reason_ru="")
            for i in range(min(deps.results_count, len(results)))
        ]

    # 5. Format.
    return build_message(point.label, results, picks, blog_evidence=blog_evidence)
