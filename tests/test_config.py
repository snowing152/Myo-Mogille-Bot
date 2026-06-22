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
    assert cfg.naver_client_id == ""
    assert cfg.naver_client_secret == ""
    assert cfg.naver_blog_evidence_enabled is False
    assert cfg.naver_blog_evidence_limit == 3


def test_load_config_overrides():
    env = dict(
        BASE_ENV,
        SEARCH_RADIUS_M="800",
        RESULTS_COUNT="5",
        SESSION_TIMEOUT_MIN="10",
        MAX_SESSION_MESSAGES="25",
        MAX_SESSION_CHARS="2000",
        TRIGGER_PHRASES="есть хочу, перекусим",
        NAVER_CLIENT_ID="naver-id",
        NAVER_CLIENT_SECRET="naver-secret",
        NAVER_BLOG_EVIDENCE_ENABLED="true",
        NAVER_BLOG_EVIDENCE_LIMIT="5",
    )
    cfg = load_config(env)
    assert cfg.search_radius_m == 800
    assert cfg.results_count == 5
    assert cfg.session_timeout_min == 10
    assert cfg.max_session_messages == 25
    assert cfg.max_session_chars == 2000
    assert cfg.trigger_phrases == ("есть хочу", "перекусим")
    assert cfg.naver_client_id == "naver-id"
    assert cfg.naver_client_secret == "naver-secret"
    assert cfg.naver_blog_evidence_enabled is True
    assert cfg.naver_blog_evidence_limit == 5


def test_load_config_missing_required():
    env = dict(BASE_ENV)
    del env["TELEGRAM_BOT_TOKEN"]
    with pytest.raises(ConfigError):
        load_config(env)


def test_load_config_bad_float_raises_config_error():
    env = dict(BASE_ENV, DEFAULT_LAT="north")
    with pytest.raises(ConfigError, match="DEFAULT_LAT"):
        load_config(env)


def test_load_config_bad_int_raises_config_error():
    env = dict(BASE_ENV, RESULTS_COUNT="many")
    with pytest.raises(ConfigError, match="RESULTS_COUNT"):
        load_config(env)


def test_load_config_rejects_out_of_range_values():
    env = dict(BASE_ENV, SEARCH_RADIUS_M="0")
    with pytest.raises(ConfigError, match="SEARCH_RADIUS_M"):
        load_config(env)

    env = dict(BASE_ENV, DEFAULT_LNG="181")
    with pytest.raises(ConfigError, match="DEFAULT_LNG"):
        load_config(env)


def test_load_config_rejects_bad_bool():
    env = dict(BASE_ENV, NAVER_BLOG_EVIDENCE_ENABLED="maybe")
    with pytest.raises(ConfigError, match="NAVER_BLOG_EVIDENCE_ENABLED"):
        load_config(env)
