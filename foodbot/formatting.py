from __future__ import annotations

import html

from foodbot.evidence import BlogEvidence
from foodbot.places import Place
from foodbot.llm import Pick


def _place_key(place: Place) -> str:
    return place.id or place.name


def _blog_evidence_summary(evidence: BlogEvidence) -> str:
    details: list[str] = []
    if evidence.matched_terms:
        details.append("еда: " + ", ".join(evidence.matched_terms[:4]))
    if evidence.prices:
        details.append("цены: " + ", ".join(evidence.prices[:2]))
    if evidence.hints:
        details.append("заметки: " + ", ".join(evidence.hints[:3]))
    if not details:
        return ""
    source_count = len(evidence.posts)
    prefix = f"📌 По блогам ({source_count}): " if source_count else "📌 По блогам: "
    return prefix + "; ".join(details)


def build_message(
    area_label: str,
    places: list[Place],
    picks: list[Pick],
    blog_evidence: dict[str, BlogEvidence] | None = None,
) -> str:
    """Telegram HTML-formatted Russian message.

    Dynamic text (place name/reason/area) is html-escaped since it
    originates from Kakao/LLM output we don't control. Must be sent with
    parse_mode="HTML" (see foodbot/handlers.py).
    """
    if not picks:
        return "Ничего подходящего не нашёл 😕 Попробуйте другие пожелания или район."

    header = f"Нашёл {len(picks)} мест рядом (район: {html.escape(area_label)}) 👇"
    blocks: list[str] = []
    for number, pick in enumerate(picks, start=1):
        place = places[pick.index]
        reason = pick.reason_ru
        head = f"{number}. {html.escape(place.name)}"
        block = head
        if reason:
            block += f"\n{html.escape(reason)}"
        evidence = (blog_evidence or {}).get(_place_key(place))
        if evidence is not None:
            summary = _blog_evidence_summary(evidence)
            if summary:
                block += f"\n{html.escape(summary)}"
        if place.url:
            block += f'\n🟡 Kakao: <a href="{html.escape(place.url)}">тык сюда</a>'
        blocks.append(block)

    return header + "\n\n" + "\n\n".join(blocks)
