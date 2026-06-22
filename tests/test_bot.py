from unittest.mock import AsyncMock

from bot import close_resources, configure_logging


def test_configure_logging_keeps_default_provider_log_levels():
    configure_logging()
    assert configure_logging() is None


async def test_close_resources_closes_kakao_client():
    kakao = AsyncMock()
    await close_resources({"kakao": kakao})
    kakao.aclose.assert_awaited_once()


async def test_close_resources_closes_naver_client():
    naver = AsyncMock()
    await close_resources({"naver": naver})
    naver.aclose.assert_awaited_once()


async def test_close_resources_ignores_missing_close_method():
    await close_resources({"kakao": object()})
