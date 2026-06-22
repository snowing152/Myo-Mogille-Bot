from foodbot.evidence import build_blog_query, collect_blog_evidence, extract_blog_evidence
from foodbot.naver import BlogPost
from foodbot.places import Place


POSTS = [
    BlogPost(
        title="명동주막 막걸리 맛집",
        description="김치전 12,000원, 파전도 있고 2차로 좋은 분위기",
        link="https://blog.example/1",
        blogger_name="blogger",
        postdate="20260620",
    ),
    BlogPost(
        title="명동 전집 후기",
        description="웨이팅 있지만 안주와 막걸리가 괜찮음",
        link="https://blog.example/2",
        blogger_name="blogger",
        postdate="20260621",
    ),
]


class FakeNaver:
    def __init__(self, posts):
        self.posts = posts
        self.calls = []

    async def search_blogs(self, query, *, display=3, sort="sim"):
        self.calls.append((query, display, sort))
        return self.posts


def test_extract_blog_evidence_finds_food_prices_and_hints():
    evidence = extract_blog_evidence(POSTS, ["막걸리", "김치전"])

    assert evidence.matched_terms[:2] == ["막걸리", "김치전"]
    assert "파전" in evidence.matched_terms
    assert "12,000원" in evidence.prices
    assert "2차" in evidence.hints
    assert "웨이팅" in evidence.hints
    assert evidence.posts[0].link == "https://blog.example/1"


def test_build_blog_query_includes_place_area_and_top_queries():
    query = build_blog_query("명동주막", "명동", ["막걸리", "김치전", "전집", "주막"])
    assert query == "명동주막 명동 막걸리 김치전 전집"


async def test_collect_blog_evidence_searches_each_place():
    place = Place("1", "명동주막", "술집", "addr", 37.5, 127.0, 100, "http://map")
    naver = FakeNaver(POSTS)

    collected = await collect_blog_evidence(
        naver, [place], "명동", ["막걸리", "김치전"], limit=2
    )

    assert naver.calls == [("명동주막 명동 막걸리 김치전", 2, "sim")]
    assert collected["1"].matched_terms[:2] == ["막걸리", "김치전"]
