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


def _require(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {key}")
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
        default_lat=float(_require(env, "DEFAULT_LAT")),
        default_lng=float(_require(env, "DEFAULT_LNG")),
        default_area_name=_require(env, "DEFAULT_AREA_NAME"),
        search_radius_m=int(env.get("SEARCH_RADIUS_M", "1500")),
        results_count=int(env.get("RESULTS_COUNT", "3")),
        session_timeout_min=int(env.get("SESSION_TIMEOUT_MIN", "20")),
        llm_model=(env.get("LLM_MODEL", "").strip() or "gemini-2.5-flash"),
        trigger_phrases=triggers,
    )
