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
