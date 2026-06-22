from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from foodbot import handlers
from foodbot.config import load_config
from foodbot.geo import GeoPoint
from foodbot.llm import GeminiLLM
from foodbot.naver import NaverClient
from foodbot.places import KakaoClient
from foodbot.session import SessionStore


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def close_resources(bot_data: dict) -> None:
    for key in ("kakao", "naver"):
        resource = bot_data.get(key)
        close = getattr(resource, "aclose", None)
        if close is not None:
            await close()


async def on_shutdown(app: Application) -> None:
    await close_resources(app.bot_data)


def build_application() -> Application:
    config = load_config()
    app = (
        Application.builder()
        .token(config.telegram_bot_token)
        .post_shutdown(on_shutdown)
        .build()
    )

    app.bot_data["config"] = config
    app.bot_data["sessions"] = SessionStore(
        timeout_min=config.session_timeout_min,
        max_messages=config.max_session_messages,
        max_chars=config.max_session_chars,
    )
    app.bot_data["kakao"] = KakaoClient(config.kakao_rest_api_key)
    app.bot_data["llm"] = GeminiLLM(api_key=config.gemini_api_key, model=config.llm_model)
    if (
        config.naver_blog_evidence_enabled
        and config.naver_client_id
        and config.naver_client_secret
    ):
        app.bot_data["naver"] = NaverClient(
            config.naver_client_id,
            config.naver_client_secret,
        )
    app.bot_data["default_point"] = GeoPoint(
        config.default_lat, config.default_lng, config.default_area_name
    )

    app.add_handler(CommandHandler("eat", handlers.on_eat))
    app.add_handler(CommandHandler("go", handlers.on_go))
    app.add_handler(CallbackQueryHandler(handlers.on_go, pattern="^find$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text))
    return app


def main() -> None:
    configure_logging()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = build_application()
    logging.getLogger(__name__).info("Bot starting (long polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
