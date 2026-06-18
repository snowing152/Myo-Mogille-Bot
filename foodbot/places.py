from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx

KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def naver_search_url(name: str) -> str:
    """Best-effort Naver Map search-by-name link (no API, no guaranteed exact match)."""
    return f"https://map.naver.com/p/search/{quote(name)}"


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    category: str
    address: str
    lat: float
    lng: float
    distance_m: int
    url: str
    phone: str = ""


def parse_kakao_response(payload: dict) -> list[Place]:
    places: list[Place] = []
    for doc in payload.get("documents", []):
        try:
            place = Place(
                id=str(doc.get("id", "")),
                name=doc.get("place_name", "") or "",
                category=doc.get("category_name", "") or "",
                address=doc.get("road_address_name") or doc.get("address_name", "") or "",
                lat=float(doc.get("y", 0.0)),
                lng=float(doc.get("x", 0.0)),
                distance_m=int(doc.get("distance") or 0),
                url=doc.get("place_url", "") or "",
                phone=doc.get("phone", "") or "",
            )
        except (TypeError, ValueError):
            continue
        if place.name:
            places.append(place)
    return places


def merge_places(results: list[list[Place]], cap: int = 20) -> list[Place]:
    seen: set[str] = set()
    merged: list[Place] = []
    for group in results:
        for place in group:
            key = place.id or place.name
            if key in seen:
                continue
            seen.add(key)
            merged.append(place)
    merged.sort(key=lambda p: p.distance_m)
    return merged[:cap]


class KakaoClient:
    def __init__(self, rest_api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = rest_api_key
        self._client = client or httpx.AsyncClient(timeout=10.0)

    async def search(
        self, query: str, lat: float, lng: float, radius_m: int, size: int = 15
    ) -> list[Place]:
        resp = await self._client.get(
            KAKAO_KEYWORD_URL,
            headers={"Authorization": f"KakaoAK {self._key}"},
            params={
                "query": query,
                "x": str(lng),
                "y": str(lat),
                "radius": str(radius_m),
                "sort": "distance",
                "size": str(size),
            },
        )
        resp.raise_for_status()
        return parse_kakao_response(resp.json())

    async def geocode(self, query: str) -> tuple[float, float] | None:
        """Resolve a place/area name to (lat, lng) via nationwide keyword search."""
        resp = await self._client.get(
            KAKAO_KEYWORD_URL,
            headers={"Authorization": f"KakaoAK {self._key}"},
            params={"query": query, "size": "1"},
        )
        resp.raise_for_status()
        places = parse_kakao_response(resp.json())
        if not places:
            return None
        return (places[0].lat, places[0].lng)

    async def aclose(self) -> None:
        await self._client.aclose()
