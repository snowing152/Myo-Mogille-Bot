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
    assert "соджу + закуски" in msg
    assert msg.count("🟡 Kakao:") == 2
    assert msg.count("🟢 Naver:") == 2
    assert msg.count("тык сюда") == 4  # 2 places x 2 links
    assert '<a href="http://map/1">тык сюда</a>' in msg
    assert '<a href="http://map/2">тык сюда</a>' in msg


def test_build_message_includes_naver_search_link():
    from foodbot.places import naver_search_url

    msg = build_message("홍대", PLACES, [Pick(0, "соджу")])
    expected_naver_url = naver_search_url("이자카야 하나")
    assert f'<a href="{expected_naver_url}">тык сюда</a>' in msg


def test_build_message_omits_kakao_line_when_url_empty():
    place_no_url = Place("3", "노 링크집", "식당", "주소", 37.5, 127.0, 100, "")
    msg = build_message("홍대", [place_no_url], [Pick(0, "что-то")])
    assert "🟡 Kakao:" not in msg
    assert "🟢 Naver:" in msg


def test_build_message_escapes_html_special_characters():
    place = Place("4", "Bar & Grill <Best>", "food", "addr", 37.5, 127.0, 100, "http://map/4")
    msg = build_message("홍대", [place], [Pick(0, "острое & вкусное")])
    assert "Bar &amp; Grill &lt;Best&gt;" in msg
    assert "острое &amp; вкусное" in msg
    assert "Bar & Grill <Best>" not in msg  # raw, unescaped text must not appear


def test_build_message_empty():
    msg = build_message("홍대", PLACES, [])
    assert "Ничего" in msg
