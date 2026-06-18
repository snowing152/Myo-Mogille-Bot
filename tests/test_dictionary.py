from foodbot.dictionary import translate_cravings


def test_translate_known_words():
    assert translate_cravings("хочу соджу и кимчи") == ["소주", "김치찌개"]


def test_translate_dedup_and_unknown():
    assert translate_cravings("пиво, ещё пиво и непонятное слово") == ["맥주"]


def test_translate_nothing():
    assert translate_cravings("привет как дела") == []
