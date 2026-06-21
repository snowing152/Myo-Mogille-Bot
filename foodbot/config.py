from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_TRIGGERS: tuple[str, ...] = (
    "куда пойдем кушать",
    "куда пойдем поесть",
    "куда пойти поесть",
    "где поедим",
    "пойдем кушать",
    "пойдем есть",
)


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    gemini_api_key: str
    kakao_rest_api_key: str
    default_lat: float
    default_lng: float
    default_area_name: str
    search_radius_m: int = 1500
    results_count: int = 3
    session_timeout_min: int = 20
    llm_model: str = "gemini-2.5-flash"
    trigger_phrases: tuple[str, ...] = DEFAULT_TRIGGERS
    max_session_messages: int = 50
    max_session_chars: int = 4000


def _require(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {key}")
    return value


def _float_env(env: dict[str, str], key: str, min_value: float, max_value: float) -> float:
    raw = _require(env, key)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a number") from exc
    if not min_value <= value <= max_value:
        raise ConfigError(f"{key} must be between {min_value} and {max_value}")
    return value


def _positive_int_env(
    env: dict[str, str],
    key: str,
    default: int,
    *,
    max_value: int | None = None,
) -> int:
    raw = env.get(key, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a positive integer") from exc
    if value <= 0:
        raise ConfigError(f"{key} must be a positive integer")
    if max_value is not None and value > max_value:
        raise ConfigError(f"{key} must be no more than {max_value}")
    return value


def load_config(env: dict[str, str] | None = None) -> Config:
    """Build a Config. Pass an explicit env dict in tests; otherwise read .env + os.environ."""
    if env is None:
        load_dotenv()
        env = dict(os.environ)

    triggers_raw = env.get("TRIGGER_PHRASES", "").strip()
    if triggers_raw:
        triggers = tuple(p.strip().lower() for p in triggers_raw.split(",") if p.strip())
    else:
        triggers = DEFAULT_TRIGGERS

    return Config(
        telegram_bot_token=_require(env, "TELEGRAM_BOT_TOKEN"),
        gemini_api_key=_require(env, "GEMINI_API_KEY"),
        kakao_rest_api_key=_require(env, "KAKAO_REST_API_KEY"),
        default_lat=_float_env(env, "DEFAULT_LAT", -90.0, 90.0),
        default_lng=_float_env(env, "DEFAULT_LNG", -180.0, 180.0),
        default_area_name=_require(env, "DEFAULT_AREA_NAME"),
        search_radius_m=_positive_int_env(env, "SEARCH_RADIUS_M", 1500, max_value=20000),
        results_count=_positive_int_env(env, "RESULTS_COUNT", 3, max_value=10),
        session_timeout_min=_positive_int_env(env, "SESSION_TIMEOUT_MIN", 20, max_value=240),
        llm_model=(env.get("LLM_MODEL", "").strip() or "gemini-2.5-flash"),
        trigger_phrases=triggers,
        max_session_messages=_positive_int_env(env, "MAX_SESSION_MESSAGES", 50, max_value=500),
        max_session_chars=_positive_int_env(env, "MAX_SESSION_CHARS", 4000, max_value=50000),
    )
