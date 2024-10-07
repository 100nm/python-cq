from asyncio import all_tasks, get_running_loop
from typing import Any

import pytest
from injection import Module as InjectionModule

from cq import MiddlewareResult
from cq._core.bus import SimpleBus, SubscriberDecorator, TaskBus


class TestSimpleBus:
    @pytest.fixture(scope="function")
    def bus(self) -> SimpleBus[Any, Any]:
        return SimpleBus()

    def test_add_middlewares_with_success_return_self(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        async def middleware(input_value: Any, /) -> MiddlewareResult[Any]:
            _ = yield  # pragma: no cover

        assert bus.add_middlewares(middleware) is bus

    def test_subscribe_with_success_return_self(self, bus: SimpleBus[Any, Any]) -> None:
        assert bus.subscribe(str, _SomeHandler) is bus

    def test_subscribe_with_already_subscribed_raise_runtime_error(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        assert bus.subscribe(str, _SomeHandler) is bus

        with pytest.raises(RuntimeError):
            bus.subscribe(str, _SomeHandler)

    async def test_dispatch_with_success_return_any(
        self,
        bus: SimpleBus[Any, str],
    ) -> None:
        bus.subscribe(str, _SomeHandler)
        input_value = "hello"
        assert await bus.dispatch(input_value) == f"|{input_value}|"

    async def test_dispatch_with_unknown_input_type_return_not_implemented(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        assert await bus.dispatch("hello") is NotImplemented

    async def test_dispatch_no_wait_with_success_return_future(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        loop = get_running_loop()
        length = len(all_tasks(loop))
        bus.dispatch_no_wait("hello")
        assert len(all_tasks(loop)) == length + 1

    async def test_subscriber_decorator_with_success(
        self,
        bus: SimpleBus[object, Any],
    ) -> None:
        module = InjectionModule().set_constant(bus)
        subscriber = SubscriberDecorator(SimpleBus[object, Any], module)

        @module.injectable
        class Dependency: ...

        @subscriber(str)
        class Handler:
            def __init__(self, dependency: Dependency) -> None:
                assert isinstance(dependency, Dependency)

            async def handle(self, input_value: str, /) -> str:
                return input_value

        value = "hello"
        assert await bus.dispatch(value) is value

    async def test_subscriber_decorator_with_bad_handler_raise_type_error(
        self,
        bus: SimpleBus[object, Any],
    ) -> None:
        module = InjectionModule().set_constant(bus)
        subscriber = SubscriberDecorator(SimpleBus[object, Any], module)

        with pytest.raises(TypeError):

            @subscriber(str)
            class BadHandler: ...


class TestTaskBus:
    @pytest.fixture(scope="function")
    def bus(self) -> TaskBus[Any]:
        return TaskBus()

    def test_subscribe_with_success_return_self(self, bus: TaskBus[Any]) -> None:
        assert bus.subscribe(str, _SomeTaskHandler) is bus
        # Checks whether several handlers can be subscribed for the same input type
        assert bus.subscribe(str, _SomeTaskHandler) is bus

    async def test_dispatch_with_success_return_none(self, bus: TaskBus[Any]) -> None:
        bus.subscribe(str, _SomeTaskHandler)

        with pytest.raises(NotImplementedError):
            await bus.dispatch("hello")

    async def test_dispatch_with_unknown_input_type_return_none(
        self,
        bus: TaskBus[Any],
    ) -> None:
        # Do nothing
        await bus.dispatch("hello")


class _SomeHandler:
    async def handle(self, input_value: str, /) -> str:
        return f"|{input_value}|"


class _SomeTaskHandler:
    async def handle(self, input_value: Any, /) -> None:
        raise NotImplementedError
