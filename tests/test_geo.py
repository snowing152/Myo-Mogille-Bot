from foodbot.geo import GeoPoint, resolve_area

DEFAULT = GeoPoint(37.5, 127.0, "Home")


class FakeKakao:
    def __init__(self, coords):
        self._coords = coords

    async def geocode(self, query):
        return self._coords


async def test_resolve_area_found():
    point = await resolve_area(FakeKakao((37.55, 126.92)), "홍대", DEFAULT)
    assert point == GeoPoint(37.55, 126.92, "홍대")


async def test_resolve_area_not_found_falls_back():
    point = await resolve_area(FakeKakao(None), "несуществующее", DEFAULT)
    assert point == DEFAULT


async def test_resolve_area_empty_falls_back():
    point = await resolve_area(FakeKakao((1.0, 2.0)), "", DEFAULT)
    assert point == DEFAULT
