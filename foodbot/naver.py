from __future__ import annotations

from dataclasses import dataclass
import html
import re

import httpx

NAVER_BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"
NAVER_LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class BlogPost:
    title: str
    description: str
    link: str
    blogger_name: str
    postdate: str


@dataclass(frozen=True)
class LocalResult:
    title: str
    category: str
    address: str
    road_address: str
    link: str


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return html.unescape(_TAG_RE.sub("", value)).strip()


def parse_blog_response(payload: dict) -> list[BlogPost]:
    posts: list[BlogPost] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        post = BlogPost(
            title=_clean_text(item.get("title")),
            description=_clean_text(item.get("description")),
            link=item.get("link", "") if isinstance(item.get("link"), str) else "",
            blogger_name=_clean_text(item.get("bloggername")),
            postdate=item.get("postdate", "") if isinstance(item.get("postdate"), str) else "",
        )
        if post.title or post.description:
            posts.append(post)
    return posts


def parse_local_response(payload: dict) -> list[LocalResult]:
    results: list[LocalResult] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        result = LocalResult(
            title=_clean_text(item.get("title")),
            category=_clean_text(item.get("category")),
            address=_clean_text(item.get("address")),
            road_address=_clean_text(item.get("roadAddress")),
            link=item.get("link", "") if isinstance(item.get("link"), str) else "",
        )
        if result.title:
            results.append(result)
    return results


class NaverClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = client or httpx.AsyncClient(timeout=10.0)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Naver-Client-Id": self._client_id,
            "X-Naver-Client-Secret": self._client_secret,
        }

    async def search_blogs(
        self,
        query: str,
        *,
        display: int = 3,
        sort: str = "sim",
    ) -> list[BlogPost]:
        resp = await self._client.get(
            NAVER_BLOG_SEARCH_URL,
            headers=self._headers(),
            params={
                "query": query,
                "display": str(display),
                "start": "1",
                "sort": sort,
            },
        )
        resp.raise_for_status()
        return parse_blog_response(resp.json())

    async def search_local(
        self,
        query: str,
        *,
        display: int = 5,
        sort: str = "comment",
    ) -> list[LocalResult]:
        resp = await self._client.get(
            NAVER_LOCAL_SEARCH_URL,
            headers=self._headers(),
            params={
                "query": query,
                "display": str(display),
                "start": "1",
                "sort": sort,
            },
        )
        resp.raise_for_status()
        return parse_local_response(resp.json())

    async def aclose(self) -> None:
        await self._client.aclose()
