from __future__ import annotations

# Lowercase Russian craving word -> Korean search query.
# Used only as a degraded fallback when the LLM is unavailable.
CRAVING_TO_KOREAN: dict[str, str] = {
    "соджу": "소주",
    "сочжу": "소주",
    "пиво": "맥주",
    "вино": "와인",
    "кимчи": "김치찌개",
    "мясо": "삼겹살",
    "самгёпсаль": "삼겹살",
    "барбекю": "고기",
    "суп": "찌개",
    "лапша": "국수",
    "рамён": "라멘",
    "рамен": "라멘",
    "суши": "스시",
    "пицца": "피자",
    "бургер": "햄버거",
    "чикен": "치킨",
    "курица": "치킨",
    "кофе": "카페",
    "десерт": "디저트",
    "сладкое": "디저트",
    "корейское": "한식",
}


def translate_cravings(text: str) -> list[str]:
    """Map recognized Russian craving words in `text` to Korean search queries.

    Returns a de-duplicated list preserving first-seen order.
    """
    lowered = text.lower()
    found: list[str] = []
    for word, korean in CRAVING_TO_KOREAN.items():
        if word in lowered and korean not in found:
            found.append(korean)
    return found
