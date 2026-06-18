from __future__ import annotations

from foodbot.places import Place
from foodbot.llm import Pick


def build_message(area_label: str, places: list[Place], picks: list[Pick]) -> str:
    """Plain-text Russian message (no Markdown -> no escaping pitfalls).

    Telegram auto-links the bare URLs.
    """
    if not picks:
        return "Ничего подходящего не нашёл 😕 Попробуйте другие пожелания или район."

    header = f"Нашёл {len(picks)} мест рядом (район: {area_label}) 👇"
    blocks: list[str] = []
    for number, pick in enumerate(picks, start=1):
        place = places[pick.index]
        reason = pick.reason_ru or place.category
        head = f"{number}. {place.name}"
        if place.category:
            head += f" ({place.category})"
        block = head
        if reason:
            block += f"\n{reason}"
        block += f"\n{place.url}"
        blocks.append(block)

    return header + "\n\n" + "\n\n".join(blocks)
