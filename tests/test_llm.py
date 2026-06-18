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
