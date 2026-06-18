from unittest.mock import AsyncMock, MagicMock

from foodbot.config import load_config
from foodbot.session import SessionStore
from foodbot import handlers, pipeline

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "t",
    "GEMINI_API_KEY": "g",
    "KAKAO_REST_API_KEY": "k",
    "DEFAULT_LAT": "37.5",
    "DEFAULT_LNG": "127.0",
    "DEFAULT_AREA_NAME": "Home",
}


def _context():
    ctx = MagicMock()
    ctx.application.bot_data = {
        "config": load_config(dict(BASE_ENV)),
        "sessions": SessionStore(timeout_min=20),
        "llm": object(),
        "kakao": object(),
        "default_point": object(),
    }
    ctx.bot.send_message = AsyncMock()
    return ctx


def _update(chat_id, text=None, callback=False):
    upd = MagicMock()
    upd.effective_chat.id = chat_id
    msg = MagicMock()
    msg.text = text
    msg.reply_text = AsyncMock()
    upd.effective_message = msg
    if callback:
        upd.callback_query = MagicMock()
        upd.callback_query.answer = AsyncMock()
    else:
        upd.callback_query = None
    return upd, msg


def _sent_texts(ctx):
    return [c.kwargs.get("text") for c in ctx.bot.send_message.await_args_list]


async def test_on_text_starts_session_on_trigger():
    ctx = _context()
    upd, msg = _update(1, "куда пойдём кушать?")
    await handlers.on_text(upd, ctx)
    assert ctx.application.bot_data["sessions"].get_active(1) is not None
    msg.reply_text.assert_awaited()


async def test_on_text_collects_messages():
    ctx = _context()
    ctx.application.bot_data["sessions"].start(1)
    upd, _ = _update(1, "хочу соджу")
    await handlers.on_text(upd, ctx)
    session = ctx.application.bot_data["sessions"].get_active(1)
    assert session.messages == ["хочу соджу"]


async def test_on_go_without_session():
    ctx = _context()
    upd, _ = _update(1, callback=True)
    await handlers.on_go(upd, ctx)
    assert any("Сессия" in (t or "") for t in _sent_texts(ctx))


async def test_on_go_runs_pipeline(monkeypatch):
    ctx = _context()
    store = ctx.application.bot_data["sessions"]
    store.start(1)
    store.get_active(1).add_message("хочу соджу")

    async def fake_run(messages, deps):
        return "РЕЗУЛЬТАТ"

    monkeypatch.setattr(pipeline, "run", fake_run)
    upd, _ = _update(1, callback=True)
    await handlers.on_go(upd, ctx)

    assert store.get_active(1) is None  # session ended
    assert any("РЕЗУЛЬТАТ" in (t or "") for t in _sent_texts(ctx))
