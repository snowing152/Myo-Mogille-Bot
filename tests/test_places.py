import httpx

from foodbot.places import Place, parse_kakao_response, merge_places, KakaoClient

SAMPLE = {
    "documents": [
        {
            "id": "1",
            "place_name": "이자카야 하나",
            "category_name": "음식점 > 술집 > 이자카야",
            "road_address_name": "서울 마포구 와우산로",
            "address_name": "서울 마포구 서교동",
            "x": "126.9220",
            "y": "37.5563",
            "distance": "250",
            "place_url": "http://place.map.kakao.com/1",
            "phone": "02-111-1111",
        },
        {  # missing place_name -> skipped
            "id": "2",
            "place_name": "",
            "x": "126.9",
            "y": "37.5",
            "distance": "10",
            "place_url": "u",
        },
    ]
}


def test_parse_kakao_response():
    places = parse_kakao_response(SAMPLE)
    assert len(places) == 1
    p = places[0]
    assert p.name == "이자카야 하나"
    assert p.distance_m == 250
    assert p.lat == 37.5563
    assert p.lng == 126.9220
    assert p.url == "http://place.map.kakao.com/1"
    assert p.phone == "02-111-1111"


def test_merge_places_dedup_sort_cap():
    a = Place("1", "A", "c", "addr", 37.5, 127.0, 300, "u")
    b = Place("2", "B", "c", "addr", 37.5, 127.0, 100, "u")
    dup = Place("1", "A", "c", "addr", 37.5, 127.0, 300, "u")
    merged = merge_places([[a, b], [dup]], cap=10)
    assert [p.id for p in merged] == ["2", "1"]


async def test_kakao_search_builds_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=SAMPLE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    kakao = KakaoClient("MYKEY", client=client)
    places = await kakao.search("소주", 37.5563, 126.9220, 1500)
    await kakao.aclose()

    assert places[0].name == "이자카야 하나"
    assert "query=" in captured["url"]
    assert "radius=1500" in captured["url"]
    assert captured["auth"] == "KakaoAK MYKEY"


def test_naver_search_url_encodes_ascii_name():
    from foodbot.places import naver_search_url

    assert naver_search_url("Cafe Mama") == "https://map.naver.com/p/search/Cafe%20Mama"


def test_naver_search_url_encodes_korean_name():
    from urllib.parse import quote

    from foodbot.places import naver_search_url

    name = "이자카야 하나"
    assert naver_search_url(name) == f"https://map.naver.com/p/search/{quote(name)}"
