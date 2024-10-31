from typing import Any

import pytest

from cq._core.middleware import MiddlewareGroup, MiddlewareResult
from cq.exceptions import MiddlewareError
from tests.helpers.history import HistoryMiddleware


class TestMiddlewareGroup:
    @pytest.fixture(scope="function")
    def group(self) -> MiddlewareGroup[..., Any]:
        return MiddlewareGroup()

    def test_add_with_success_return_self(
        self,
        group: MiddlewareGroup[..., Any],
        history: HistoryMiddleware,
    ) -> None:
        assert group.add(history) is group

    async def test_invoke_with_success_return_any(
        self,
        group: MiddlewareGroup[..., Any],
        history: HistoryMiddleware,
    ) -> None:
        async def handler() -> str:
            return "I'm a handler..."

        group.add(history)
        result = await group.invoke(handler)

        records = history.records
        assert len(records) == 1

        record = records[0]
        assert record.args == ()
        assert record.kwargs == {}
        assert record.result == result
        assert record.is_success

    async def test_invoke_with_exception_raise_any(
        self,
        group: MiddlewareGroup[..., Any],
        history: HistoryMiddleware,
    ) -> None:
        async def handler() -> str:
            raise ValueError("I failed...")

        group.add(history)

        with pytest.raises(ValueError):
            await group.invoke(handler)

        records = history.records
        assert len(records) == 1

        record = records[0]
        assert record.args == ()
        assert record.kwargs == {}
        assert isinstance(record.result, ValueError)
        assert record.is_failed

    async def test_invoke_with_too_many_yield_raise_middleware_error(
        self,
        group: MiddlewareGroup[..., Any],
    ) -> None:
        async def handler() -> None: ...

        async def too_many_yield_middleware(
            *args: Any,
            **kwargs: Any,
        ) -> MiddlewareResult[Any]:
            yield
            yield

        group.add(too_many_yield_middleware)

        with pytest.raises(MiddlewareError):
            await group.invoke(handler)

    async def test_invoke_with_multiple_yield_return_any(
        self,
        group: MiddlewareGroup[..., Any],
        history: HistoryMiddleware,
    ) -> None:
        async def handler() -> str:
            raise ValueError()

        group.add(_exec_2_times_middleware, history)

        with pytest.raises(ValueError):
            await group.invoke(handler)

        records = history.records
        assert len(records) == 2


async def _exec_2_times_middleware(*args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
    try:
        yield
    except ValueError:
        yield
