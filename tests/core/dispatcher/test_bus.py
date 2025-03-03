from typing import Any, Self

import pytest

from cq import MiddlewareResult
from cq._core.dispatcher.bus import SimpleBus, TaskBus


class TestSimpleBus:
    def test_add_middlewares_with_success_return_self(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        async def middleware(input_value: Any, /) -> MiddlewareResult[Any]:
            _ = yield  # pragma: no cover

        assert bus.add_middlewares(middleware) is bus

    def test_subscribe_with_success_return_self(self, bus: SimpleBus[Any, Any]) -> None:
        assert bus.subscribe(str, _SomeHandler.async_factory) is bus

    def test_subscribe_with_already_subscribed_raise_runtime_error(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        assert bus.subscribe(str, _SomeHandler.async_factory) is bus

        with pytest.raises(RuntimeError):
            bus.subscribe(str, _SomeHandler.async_factory)

    async def test_dispatch_with_success_return_any(
        self,
        bus: SimpleBus[Any, str],
    ) -> None:
        bus.subscribe(str, _SomeHandler.async_factory)
        input_value = "hello"
        assert await bus.dispatch(input_value) == f"|{input_value}|"

    async def test_dispatch_with_unknown_input_type_return_not_implemented(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        assert await bus.dispatch("hello") is NotImplemented

    async def test_dispatch_with_listeners_return_none(
        self,
        bus: SimpleBus[object, Any],
    ) -> None:
        called = False

        async def listener(_: Any) -> None:
            nonlocal called
            called = True

        bus.add_listeners(listener)
        assert await bus.dispatch("hello") is NotImplemented
        assert called


class TestTaskBus:
    @pytest.fixture(scope="function")
    def task_bus(self) -> TaskBus[Any]:
        return TaskBus()

    def test_subscribe_with_success_return_self(self, task_bus: TaskBus[Any]) -> None:
        assert task_bus.subscribe(str, _SomeTaskHandler.async_factory) is task_bus
        # Checks whether several handlers can be subscribed for the same input type
        assert task_bus.subscribe(str, _SomeTaskHandler.async_factory) is task_bus

    async def test_dispatch_with_success_return_none(
        self,
        task_bus: TaskBus[Any],
    ) -> None:
        task_bus.subscribe(str, _SomeTaskHandler.async_factory)

        with pytest.raises(ExceptionGroup):
            await task_bus.dispatch("hello")

    async def test_dispatch_with_unknown_input_type_return_none(
        self,
        task_bus: TaskBus[Any],
    ) -> None:
        # Do nothing
        await task_bus.dispatch("hello")


class _SomeHandler:
    async def handle(self, input_value: str, /) -> str:
        return f"|{input_value}|"

    @classmethod
    async def async_factory(cls) -> Self:
        return cls()


class _SomeTaskHandler:
    async def handle(self, input_value: Any, /) -> None:
        raise NotImplementedError

    @classmethod
    async def async_factory(cls) -> Self:
        return cls()
