from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from foodbot.naver import BlogPost

FOOD_TERMS: tuple[str, ...] = (
    "막걸리",
    "김치전",
    "파전",
    "해물파전",
    "전집",
    "안주",
    "소주",
    "맥주",
    "치킨",
    "삼겹살",
    "고기",
    "찌개",
    "국수",
    "라멘",
    "스시",
    "피자",
    "햄버거",
    "디저트",
    "카페",
)
HINT_TERMS: tuple[str, ...] = (
    "가성비",
    "분위기",
    "데이트",
    "회식",
    "2차",
    "웨이팅",
    "예약",
    "혼밥",
    "친절",
    "현지인",
    "맛집",
)
PRICE_RE = re.compile(r"(?:₩\s?\d[\d,]*|\d[\d,]*(?:원|천원|만원)|\d+(?:\.\d+)?\s?만)")


@dataclass(frozen=True)
class BlogEvidencePost:
    title: str
    description: str
    link: str
    postdate: str
    matched_terms: list[str]
    prices: list[str]
    hints: list[str]


@dataclass
class BlogEvidence:
    posts: list[BlogEvidencePost] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    prices: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _terms_from_text(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def extract_blog_evidence(posts: list[BlogPost], search_terms: list[str]) -> BlogEvidence:
    terms = _dedupe([term.strip() for term in search_terms if len(term.strip()) > 1] + list(FOOD_TERMS))
    evidence = BlogEvidence()
    for post in posts:
        text = f"{post.title} {post.description}"
        matched_terms = _terms_from_text(text, terms)
        prices = PRICE_RE.findall(text)
        hints = _terms_from_text(text, list(HINT_TERMS))
        evidence.posts.append(
            BlogEvidencePost(
                title=post.title,
                description=post.description,
                link=post.link,
                postdate=post.postdate,
                matched_terms=matched_terms,
                prices=prices,
                hints=hints,
            )
        )
        evidence.matched_terms.extend(matched_terms)
        evidence.prices.extend(prices)
        evidence.hints.extend(hints)
    evidence.matched_terms = _dedupe(evidence.matched_terms)
    evidence.prices = _dedupe(evidence.prices)
    evidence.hints = _dedupe(evidence.hints)
    return evidence


def build_blog_query(place_name: str, area_label: str, queries: list[str]) -> str:
    parts = [place_name, area_label, *queries[:3]]
    return " ".join(part for part in parts if part).strip()


async def collect_blog_evidence(
    naver: Any,
    places: list[Any],
    area_label: str,
    queries: list[str],
    *,
    limit: int,
) -> dict[str, BlogEvidence]:
    collected: dict[str, BlogEvidence] = {}
    for place in places:
        query = build_blog_query(place.name, area_label, queries)
        posts = await naver.search_blogs(query, display=limit)
        key = place.id or place.name
        collected[key] = extract_blog_evidence(posts, queries)
    return collected
