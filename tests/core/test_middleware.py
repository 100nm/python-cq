from __future__ import annotations

from collections.abc import Mapping
from enum import IntEnum
from typing import Any, NamedTuple

import pytest

from cq._core.middleware import MiddlewareGroup, MiddlewareResult


class TestMiddlewareGroup:
    @pytest.fixture(scope="function")
    def group(self) -> MiddlewareGroup[..., Any]:
        return MiddlewareGroup()

    @pytest.fixture(scope="function")
    def history(self) -> _HistoryMiddleware:
        return _HistoryMiddleware()

    def test_add_with_success_return_self(
        self,
        group: MiddlewareGroup[..., Any],
        history: _HistoryMiddleware,
    ) -> None:
        assert group.add(history) is group

    async def test_invoke_with_success_return_any(
        self,
        group: MiddlewareGroup[..., Any],
        history: _HistoryMiddleware,
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
        assert record.status == _Status.SUCCESS

    async def test_invoke_with_exception_raise_any(
        self,
        group: MiddlewareGroup[..., Any],
        history: _HistoryMiddleware,
    ) -> None:
        async def handler() -> str:
            raise ValueError("I failed...")

        group.add(history)
        assert await group.invoke(handler) is NotImplemented

        records = history.records
        assert len(records) == 1

        record = records[0]
        assert record.args == ()
        assert record.kwargs == {}
        assert isinstance(record.result, ValueError)
        assert record.status == _Status.FAILED


class _Status(IntEnum):
    SUCCESS = 1
    FAILED = 0


class _Record(NamedTuple):
    args: tuple[Any, ...]
    kwargs: Mapping[str, Any]
    result: Any
    status: _Status


class _HistoryMiddleware:
    def __init__(self) -> None:
        self.__records: list[_Record] = []

    @property
    def records(self) -> tuple[_Record, ...]:
        return tuple(self.__records)

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        try:
            result = yield
        except BaseException as exc:
            record = _Record(args, kwargs, exc, _Status.FAILED)
        else:
            record = _Record(args, kwargs, result, _Status.SUCCESS)

        self.__records.append(record)
