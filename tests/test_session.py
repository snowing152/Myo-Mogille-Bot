from foodbot.config import DEFAULT_TRIGGERS
from foodbot.session import (
    is_trigger,
    normalize,
    Session,
    SessionStore,
    SessionState,
)


def test_normalize_lowercases_and_replaces_yo():
    assert normalize("ПойдЁм") == "пойдем"


def test_is_trigger_matches_variants():
    assert is_trigger("Ну что, куда пойдём кушать?", DEFAULT_TRIGGERS)
    assert is_trigger("ГДЕ ПОЕДИМ сегодня", DEFAULT_TRIGGERS)


def test_is_trigger_no_match():
    assert not is_trigger("сегодня хорошая погода", DEFAULT_TRIGGERS)


def test_session_store_lifecycle():
    clock = {"t": 100.0}
    store = SessionStore(timeout_min=20, now=lambda: clock["t"])
    assert store.get_active(1) is None

    session = store.start(1)
    assert session.state == SessionState.COLLECTING

    store.get_active(1).add_message("хочу соджу")
    store.get_active(1).add_message("   ")  # blank ignored
    assert store.get_active(1).messages == ["хочу соджу"]

    store.end(1)
    assert store.get_active(1) is None


def test_session_expiry():
    clock = {"t": 0.0}
    store = SessionStore(timeout_min=20, now=lambda: clock["t"])
    store.start(1)
    clock["t"] = 21 * 60  # 21 minutes later
    assert store.get_active(1) is None
