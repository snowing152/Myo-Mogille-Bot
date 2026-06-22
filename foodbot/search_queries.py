from __future__ import annotations


EXPANSIONS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("막걸리",), ("막걸리집", "전집", "주막", "요리주점")),
    (("김치전", "파전", "전"), ("전집", "막걸리집", "주막")),
    (("소주",), ("이자카야", "포차", "요리주점", "술집")),
    (("맥주",), ("호프", "치킨", "술집")),
    (("와인",), ("와인바", "양식")),
    (("삼겹살", "고기", "바베큐"), ("고기집", "구이", "한식")),
    (("치킨",), ("치킨", "호프")),
    (("라멘",), ("라멘", "일식")),
    (("국수",), ("국수", "분식")),
    (("디저트",), ("디저트", "카페")),
    (("카페",), ("카페",)),
)


def expand_search_queries(queries: list[str], limit: int = 10) -> list[str]:
    """Add place-intent Korean queries while preserving caller order."""
    expanded: list[str] = []

    def add(query: str) -> None:
        normalized = query.strip()
        if normalized and normalized not in expanded:
            expanded.append(normalized)

    for query in queries:
        add(query)
        for needles, additions in EXPANSIONS:
            if any(needle in query for needle in needles):
                for addition in additions:
                    add(addition)
        if len(expanded) >= limit:
            break

    return expanded[:limit]
