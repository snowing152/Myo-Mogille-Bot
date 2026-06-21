from unittest.mock import AsyncMock

from bot import close_resources


async def test_close_resources_closes_kakao_client():
    kakao = AsyncMock()
    await close_resources({"kakao": kakao})
    kakao.aclose.assert_awaited_once()


async def test_close_resources_ignores_missing_close_method():
    await close_resources({"kakao": object()})
