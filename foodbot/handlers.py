from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from foodbot import pipeline
from foodbot.geo import GeoPoint
from foodbot.session import is_trigger

logger = logging.getLogger(__name__)

START_PROMPT = (
    "Окей, собираю пожелания! 🍽 Пишите, что хотите — соджу, кимчи, мясо… "
    "Можно указать район (например «в Хондэ»). Когда готовы — жмите кнопку."
)
FIND_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🍽 Найти места", callback_data="find")]]
)
NO_SESSION = "Сессия истекла или не начата. Напишите «куда пойдём кушать?» заново."
NO_MESSAGES = "Пока никто не написал пожеланий 🤔 Напишите, что хотите, потом жмите кнопку."
SEARCHING = "Секунду, ищу подходящие места… 🔎"
ERROR = "Упс, что-то пошло не так. Попробуйте ещё раз чуть позже."


def _build_deps(context: ContextTypes.DEFAULT_TYPE) -> pipeline.PipelineDeps:
    bot_data = context.application.bot_data
    config = bot_data["config"]
    return pipeline.PipelineDeps(
        llm=bot_data["llm"],
        kakao=bot_data["kakao"],
        default_point=bot_data["default_point"],
        radius_m=config.search_radius_m,
        results_count=config.results_count,
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    chat_id = update.effective_chat.id
    config = context.application.bot_data["config"]
    sessions = context.application.bot_data["sessions"]

    if is_trigger(message.text, config.trigger_phrases):
        sessions.start(chat_id)
        await message.reply_text(START_PROMPT, reply_markup=FIND_BUTTON)
        return

    session = sessions.get_active(chat_id)
    if session is not None:
        session.add_message(message.text)


async def on_eat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    context.application.bot_data["sessions"].start(chat_id)
    await context.bot.send_message(chat_id=chat_id, text=START_PROMPT, reply_markup=FIND_BUTTON)


async def on_go(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query is not None:
        await update.callback_query.answer()
    chat_id = update.effective_chat.id
    sessions = context.application.bot_data["sessions"]
    session = sessions.get_active(chat_id)

    if session is None:
        await context.bot.send_message(chat_id=chat_id, text=NO_SESSION)
        return
    if not session.messages:
        await context.bot.send_message(chat_id=chat_id, text=NO_MESSAGES)
        return

    messages = list(session.messages)
    sessions.end(chat_id)
    await context.bot.send_message(chat_id=chat_id, text=SEARCHING)
    try:
        reply = await pipeline.run(messages, _build_deps(context))
    except Exception:
        logger.exception("pipeline failed")
        reply = ERROR
    await context.bot.send_message(chat_id=chat_id, text=reply)
