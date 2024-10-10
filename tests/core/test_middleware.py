from __future__ import annotations

from typing import Any

import pytest

from cq._core.middleware import MiddlewareGroup, MiddlewareResult
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

    async def test_invoke_with_multiple_yield_return_any(
        self,
        group: MiddlewareGroup[..., Any],
        history: HistoryMiddleware,
    ) -> None:
        async def handler() -> str:
            return "I'm a handler..."

        group.add(_exec_2_times_middleware, history)
        await group.invoke(handler)

        records = history.records
        assert len(records) == 2


async def _exec_2_times_middleware(*args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
    yield
    yield
