import httpx

from foodbot.naver import NaverClient, parse_blog_response, parse_local_response


async def test_naver_blog_search_builds_request():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["client_id"] = request.headers.get("X-Naver-Client-Id")
        captured["client_secret"] = request.headers.get("X-Naver-Client-Secret")
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "title": "<b>명동주막</b>",
                        "description": "막걸리 &amp; 김치전",
                        "link": "https://blog.example/post",
                        "bloggername": "맛집블로그",
                        "postdate": "20260621",
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    naver = NaverClient("id", "secret", client=client)
    posts = await naver.search_blogs("명동주막 막걸리", display=2)

    assert captured["url"].startswith("https://openapi.naver.com/v1/search/blog.json")
    assert "query=%EB%AA%85%EB%8F%99%EC%A3%BC%EB%A7%89" in captured["url"]
    assert "display=2" in captured["url"]
    assert captured["client_id"] == "id"
    assert captured["client_secret"] == "secret"
    assert posts[0].title == "명동주막"
    assert posts[0].description == "막걸리 & 김치전"


async def test_naver_local_search_builds_request():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "title": "<b>명동주막</b>",
                        "category": "음식점&gt;술집",
                        "address": "서울 중구",
                        "roadAddress": "서울 중구 명동길",
                        "link": "https://map.naver.com/example",
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    naver = NaverClient("id", "secret", client=client)
    results = await naver.search_local("명동주막", display=1)

    assert captured["url"].startswith("https://openapi.naver.com/v1/search/local.json")
    assert "sort=comment" in captured["url"]
    assert results[0].title == "명동주막"
    assert results[0].category == "음식점>술집"


def test_parse_blog_response_filters_bad_items_and_cleans_html():
    posts = parse_blog_response(
        {
            "items": [
                "bad",
                {"title": "", "description": ""},
                {"title": "A &amp; B", "description": "<b>막걸리</b>"},
            ]
        }
    )

    assert len(posts) == 1
    assert posts[0].title == "A & B"
    assert posts[0].description == "막걸리"


def test_parse_local_response_filters_bad_items_and_cleans_html():
    results = parse_local_response(
        {
            "items": [
                {"title": "", "category": "음식점"},
                {"title": "<b>술집</b>", "category": "술집&gt;요리주점"},
            ]
        }
    )

    assert len(results) == 1
    assert results[0].title == "술집"
    assert results[0].category == "술집>요리주점"
