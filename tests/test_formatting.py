from foodbot.places import Place
from foodbot.llm import Pick
from foodbot.formatting import build_message

PLACES = [
    Place("1", "이자카야 하나", "술집", "주소", 37.5, 127.0, 250, "http://map/1"),
    Place("2", "삼겹살집", "고기", "주소", 37.5, 127.0, 400, "http://map/2"),
]


def test_build_message_lists_picks():
    msg = build_message("홍대", PLACES, [Pick(0, "соджу + закуски"), Pick(1, "мясо")])
    assert "홍대" in msg
    assert "이자카야 하나" in msg
    assert "삼겹살집" in msg
    assert "http://map/1" in msg
    assert "соджу + закуски" in msg
    assert msg.count("http://map/") == 2


def test_build_message_empty():
    msg = build_message("홍대", PLACES, [])
    assert "Ничего" in msg
