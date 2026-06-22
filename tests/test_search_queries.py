from foodbot.search_queries import expand_search_queries


def test_expand_search_queries_adds_place_intent_for_makgeolli_and_jeon():
    queries = expand_search_queries(["막걸리", "김치전"])
    assert queries[:5] == ["막걸리", "막걸리집", "전집", "주막", "요리주점"]
    assert "김치전" in queries


def test_expand_search_queries_preserves_order_and_deduplicates():
    queries = expand_search_queries(["소주", "술집", "소주"])
    assert queries == ["소주", "이자카야", "포차", "요리주점", "술집"]


def test_expand_search_queries_respects_limit():
    queries = expand_search_queries(["막걸리", "소주", "맥주"], limit=4)
    assert queries == ["막걸리", "막걸리집", "전집", "주막"]
