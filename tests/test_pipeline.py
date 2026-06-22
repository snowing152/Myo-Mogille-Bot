from foodbot.geo import GeoPoint
from foodbot.places import Place
from foodbot.llm import CravingResult, Pick
from foodbot.naver import BlogPost
from foodbot import pipeline

DEFAULT = GeoPoint(37.5, 127.0, "Home")
P1 = Place("1", "이자카야", "술집", "addr", 37.5, 127.0, 250, "http://m/1")
P2 = Place("2", "전집", "한식", "addr", 37.5, 127.0, 350, "http://m/2")


class FakeKakao:
    def __init__(self, by_query, coords=None, fail_queries=None):
        self.by_query = by_query
        self._coords = coords
        self.fail_queries = set(fail_queries or ())
        self.searches = []

    async def search(self, query, lat, lng, radius_m, size=15):
        self.searches.append(query)
        if query in self.fail_queries:
            raise RuntimeError("kakao down")
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

    async def rank_places(self, cravings, places, count, evidence_lines=None):
        if self._fail_rank:
            raise RuntimeError("llm down")
        return self._picks


class FakeNaver:
    def __init__(self, fail=False, posts_by_prefix=None):
        self.fail = fail
        self.posts_by_prefix = posts_by_prefix or {}
        self.calls = []

    async def search_blogs(self, query, *, display=3, sort="sim"):
        self.calls.append((query, display, sort))
        if self.fail:
            raise RuntimeError("naver down")
        for prefix, posts in self.posts_by_prefix.items():
            if query.startswith(prefix):
                return posts
        return []


def _deps(llm, kakao, results_count=3, **overrides):
    return pipeline.PipelineDeps(
        llm=llm,
        kakao=kakao,
        default_point=DEFAULT,
        radius_m=1500,
        results_count=results_count,
        **overrides,
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


async def test_pipeline_all_searches_fail_returns_provider_error():
    llm = FakeLLM(extract=CravingResult(["soju"], ["소주"], None, False))
    msg = await pipeline.run(["соджу"], _deps(llm, FakeKakao({}, fail_queries={"소주"})))
    assert "временно не могу проверить места" in msg


async def test_pipeline_partial_search_failure_uses_successful_results():
    llm = FakeLLM(
        extract=CravingResult(["soju", "meat"], ["소주", "삼겹살"], None, False),
        picks=[Pick(0, "мясо")],
    )
    kakao = FakeKakao({"삼겹살": [P1]}, fail_queries={"소주"})
    msg = await pipeline.run(["соджу и мясо"], _deps(llm, kakao))
    assert "이자카야" in msg
    assert "мясо" in msg


async def test_pipeline_partial_search_failure_without_results_returns_provider_error():
    llm = FakeLLM(
        extract=CravingResult(["soju", "meat"], ["소주", "삼겹살"], None, False),
    )
    kakao = FakeKakao({"소주": []}, fail_queries={"삼겹살"})
    msg = await pipeline.run(["соджу и мясо"], _deps(llm, kakao))
    assert "временно не могу проверить места" in msg


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
    assert "술집" not in msg


async def test_pipeline_searches_expanded_place_intent_queries():
    llm = FakeLLM(
        extract=CravingResult(["makgeolli", "kimchijeon"], ["막걸리", "김치전"], None, False),
        picks=[Pick(0, "макколи")],
    )
    kakao = FakeKakao({"전집": [P1]})
    msg = await pipeline.run(["макколи и кимчичон"], _deps(llm, kakao))
    assert "이자카야" in msg
    assert "막걸리" in kakao.searches
    assert "전집" in kakao.searches


async def test_search_all_tracks_query_provenance_and_best_rank():
    kakao = FakeKakao({"막걸리": [P2, P1], "전집": [P1]})
    batch = await pipeline._search_all(kakao, ["막걸리", "전집"], DEFAULT, 1500)

    assert batch.places == [P1, P2]
    assert batch.evidence[P1.id].queries == ["막걸리", "전집"]
    assert batch.evidence[P1.id].best_rank == 1
    assert batch.evidence[P1.id].first_radius_m == 1500
    assert batch.evidence[P2.id].queries == ["막걸리"]


async def test_pipeline_collects_naver_blog_evidence_when_enabled():
    llm = FakeLLM(
        extract=CravingResult(["soju"], ["소주"], None, False),
        picks=[Pick(0, "соджу")],
    )
    naver = FakeNaver()
    msg = await pipeline.run(
        ["соджу"],
        _deps(
            llm,
            FakeKakao({"소주": [P1]}),
            naver=naver,
            naver_blog_evidence_enabled=True,
            naver_blog_evidence_limit=2,
        ),
    )

    assert "이자카야" in msg
    assert naver.calls == [("이자카야 Home 소주", 2, "sim")]


async def test_pipeline_ignores_naver_blog_evidence_failure():
    llm = FakeLLM(
        extract=CravingResult(["soju"], ["소주"], None, False),
        picks=[Pick(0, "соджу")],
    )
    msg = await pipeline.run(
        ["соджу"],
        _deps(
            llm,
            FakeKakao({"소주": [P1]}),
            naver=FakeNaver(fail=True),
            naver_blog_evidence_enabled=True,
        ),
    )

    assert "이자카야" in msg


async def test_pipeline_pre_ranks_candidates_with_blog_evidence():
    llm = FakeLLM(
        extract=CravingResult(["makgeolli", "kimchijeon"], ["막걸리", "김치전"], None, False),
        fail_rank=True,
    )
    naver = FakeNaver(
        posts_by_prefix={
            "전집": [
                BlogPost(
                    title="전집 막걸리 김치전",
                    description="파전 12,000원, 2차로 좋은 분위기",
                    link="https://blog.example/1",
                    blogger_name="blogger",
                    postdate="20260620",
                )
            ]
        }
    )
    msg = await pipeline.run(
        ["макколи и кимчичон"],
        _deps(
            llm,
            FakeKakao({"막걸리": [P1, P2]}),
            naver=naver,
            naver_blog_evidence_enabled=True,
        ),
    )

    assert msg.index("전집") < msg.index("이자카야")
