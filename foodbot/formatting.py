from __future__ import annotations

import html

from foodbot.places import Place, naver_search_url
from foodbot.llm import Pick


def build_message(area_label: str, places: list[Place], picks: list[Pick]) -> str:
    """Telegram HTML-formatted Russian message.

    Dynamic text (place name/category/reason/area) is html-escaped since it
    originates from Kakao/LLM output we don't control. Must be sent with
    parse_mode="HTML" (see foodbot/handlers.py).
    """
    if not picks:
        return "Ничего подходящего не нашёл 😕 Попробуйте другие пожелания или район."

    header = f"Нашёл {len(picks)} мест рядом (район: {html.escape(area_label)}) 👇"
    blocks: list[str] = []
    for number, pick in enumerate(picks, start=1):
        place = places[pick.index]
        reason = pick.reason_ru or place.category
        head = f"{number}. {html.escape(place.name)}"
        if place.category:
            head += f" ({html.escape(place.category)})"
        block = head
        if reason:
            block += f"\n{html.escape(reason)}"
        if place.url:
            block += f'\n🟡 Kakao: <a href="{html.escape(place.url)}">тык сюда</a>'
        naver_url = naver_search_url(place.name)
        block += f'\n🟢 Naver: <a href="{html.escape(naver_url)}">тык сюда</a>'
        blocks.append(block)

    return header + "\n\n" + "\n\n".join(blocks)
