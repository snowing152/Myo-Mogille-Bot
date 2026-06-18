from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lng: float
    label: str


class _Geocoder(Protocol):
    async def geocode(self, query: str) -> tuple[float, float] | None: ...


async def resolve_area(kakao: _Geocoder, area: str, default: GeoPoint) -> GeoPoint:
    """Resolve a neighborhood name to a GeoPoint, falling back to `default`."""
    area = (area or "").strip()
    if not area:
        return default
    coords = await kakao.geocode(area)
    if coords is None:
        return default
    return GeoPoint(lat=coords[0], lng=coords[1], label=area)
