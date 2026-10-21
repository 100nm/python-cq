import pytest

from cq._core.middleware import MiddlewareGroup
from cq.middlewares.retry import RetryMiddleware


class TestRetryMiddleware:
    @pytest.mark.parametrize("retry", [0, -1])
    def test_init_with_retry_less_than_1_raises_value_error(self, retry: int) -> None:
        with pytest.raises(ValueError, match="`retry` must be at least 1"):
            RetryMiddleware(retry)

    async def test_call_without_error_calls_handler_once(self) -> None:
        attempts: list[int] = []

        async def handler() -> str:
            attempts.append(len(attempts) + 1)
            return "success"

        group = MiddlewareGroup[[], str]().add(RetryMiddleware(3))

        assert await group.invoke(handler) == "success"
        assert attempts == [1]

    async def test_call_with_transient_error_returns_handler_result(self) -> None:
        attempts: list[int] = []

        async def handler() -> str:
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                raise ValueError

            return "success"

        group = MiddlewareGroup[[], str]().add(RetryMiddleware(3))

        assert await group.invoke(handler) == "success"
        assert attempts == [1, 2, 3]

    async def test_call_with_persistent_error_raises_error_after_last_attempt(
        self,
    ) -> None:
        attempts: list[int] = []

        async def handler() -> None:
            attempts.append(len(attempts) + 1)
            raise ValueError

        group = MiddlewareGroup[[], None]().add(RetryMiddleware(3))

        with pytest.raises(ValueError):
            await group.invoke(handler)

        assert attempts == [1, 2, 3]

    async def test_call_with_unhandled_error_raises_error_without_retry(
        self,
    ) -> None:
        attempts: list[int] = []

        async def handler() -> None:
            attempts.append(len(attempts) + 1)
            raise ValueError

        middleware = RetryMiddleware(3, exceptions=[KeyError])
        group = MiddlewareGroup[[], None]().add(middleware)

        with pytest.raises(ValueError):
            await group.invoke(handler)

        assert attempts == [1]
