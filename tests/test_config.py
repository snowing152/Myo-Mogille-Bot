import pytest

from foodbot.config import load_config, Config, ConfigError, DEFAULT_TRIGGERS

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "tok",
    "GEMINI_API_KEY": "gem",
    "KAKAO_REST_API_KEY": "kak",
    "DEFAULT_LAT": "37.5",
    "DEFAULT_LNG": "127.0",
    "DEFAULT_AREA_NAME": "Hongdae",
}


def test_load_config_defaults():
    cfg = load_config(dict(BASE_ENV))
    assert isinstance(cfg, Config)
    assert cfg.telegram_bot_token == "tok"
    assert cfg.default_lat == 37.5
    assert cfg.default_lng == 127.0
    assert cfg.search_radius_m == 1500
    assert cfg.results_count == 3
    assert cfg.session_timeout_min == 20
    assert cfg.llm_model == "gemini-2.5-flash"
    assert cfg.trigger_phrases == DEFAULT_TRIGGERS


def test_load_config_overrides():
    env = dict(
        BASE_ENV,
        SEARCH_RADIUS_M="800",
        RESULTS_COUNT="5",
        TRIGGER_PHRASES="есть хочу, перекусим",
    )
    cfg = load_config(env)
    assert cfg.search_radius_m == 800
    assert cfg.results_count == 5
    assert cfg.trigger_phrases == ("есть хочу", "перекусим")


def test_load_config_missing_required():
    env = dict(BASE_ENV)
    del env["TELEGRAM_BOT_TOKEN"]
    with pytest.raises(ConfigError):
        load_config(env)
