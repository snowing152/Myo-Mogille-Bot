from foodbot.places import Place
from foodbot.llm import Pick
from foodbot.evidence import BlogEvidence, BlogEvidencePost
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
    assert "술집" not in msg
    assert "고기" not in msg
    assert "соджу + закуски" in msg
    assert msg.count("🟡 Kakao:") == 2
    assert msg.count("тык сюда") == 2
    assert '<a href="http://map/1">тык сюда</a>' in msg
    assert '<a href="http://map/2">тык сюда</a>' in msg


def test_build_message_omits_kakao_line_when_url_empty():
    place_no_url = Place("3", "노 링크집", "식당", "주소", 37.5, 127.0, 100, "")
    msg = build_message("홍대", [place_no_url], [Pick(0, "что-то")])
    assert "🟡 Kakao:" not in msg
    assert "식당" not in msg


def test_build_message_escapes_html_special_characters():
    place = Place("4", "Bar & Grill <Best>", "food", "addr", 37.5, 127.0, 100, "http://map/4")
    msg = build_message("홍대", [place], [Pick(0, "острое & вкусное")])
    assert "Bar &amp; Grill &lt;Best&gt;" in msg
    assert "острое &amp; вкусное" in msg
    assert "Bar & Grill <Best>" not in msg  # raw, unescaped text must not appear


def test_build_message_adds_escaped_blog_evidence_summary():
    evidence = BlogEvidence(
        posts=[
            BlogEvidencePost(
                title="blog",
                description="desc",
                link="https://blog.example",
                postdate="20260620",
                matched_terms=[],
                prices=[],
                hints=[],
            )
        ],
        matched_terms=["막걸리", "김치전"],
        prices=["12,000원"],
        hints=["2차", "분위기 & 맛집"],
    )
    msg = build_message("홍대", PLACES, [Pick(0, "")], blog_evidence={"1": evidence})
    assert "По блогам (1)" in msg
    assert "еда: 막걸리, 김치전" in msg
    assert "цены: 12,000원" in msg
    assert "분위기 &amp; 맛집" in msg


def test_build_message_empty():
    msg = build_message("홍대", PLACES, [])
    assert "Ничего" in msg
