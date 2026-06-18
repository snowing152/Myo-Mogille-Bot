from __future__ import annotations

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
from foodbot.places import KakaoClient
from foodbot.session import SessionStore


def build_application() -> Application:
    config = load_config()
    app = Application.builder().token(config.telegram_bot_token).build()

    app.bot_data["config"] = config
    app.bot_data["sessions"] = SessionStore(timeout_min=config.session_timeout_min)
    app.bot_data["kakao"] = KakaoClient(config.kakao_rest_api_key)
    app.bot_data["llm"] = GeminiLLM(api_key=config.gemini_api_key, model=config.llm_model)
    app.bot_data["default_point"] = GeoPoint(
        config.default_lat, config.default_lng, config.default_area_name
    )

    app.add_handler(CommandHandler("eat", handlers.on_eat))
    app.add_handler(CommandHandler("go", handlers.on_go))
    app.add_handler(CallbackQueryHandler(handlers.on_go, pattern="^find$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text))
    return app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = build_application()
    logging.getLogger(__name__).info("Bot starting (long polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
