from contextlib import nullcontext
from typing import Any, Self

import pytest

from cq import MiddlewareResult
from cq._core.routing.dispatchers.bus import SimpleBus, TaskBus
from cq.middlewares.contextlib import ContextManagerMiddleware


class _UpperHandler:
    async def handle(self, message: str) -> str:
        return message.upper()

    @classmethod
    async def factory(cls) -> Self:
        return cls()


class _FailingHandler:
    async def handle(self, message: str) -> None:
        raise ValueError(message)

    @classmethod
    async def factory(cls) -> Self:
        return cls()


class TestSimpleBus:
    def test_add_listeners_with_success_returns_self(self) -> None:
        async def listener(message: str) -> None: ...

        bus = SimpleBus[str, str]()

        assert bus.add_listeners(listener) is bus

    def test_add_middlewares_with_success_returns_self(self) -> None:
        middleware = ContextManagerMiddleware(nullcontext())
        bus = SimpleBus[str, str]()

        assert bus.add_middlewares(middleware) is bus

    def test_subscribe_with_success_returns_self(self) -> None:
        bus = SimpleBus[str, str]()

        assert bus.subscribe(str, _UpperHandler.factory) is bus

    async def test_call_with_success_returns_handler_result(self) -> None:
        bus = SimpleBus[str, str]().subscribe(str, _UpperHandler.factory)

        assert await bus("hello") == "HELLO"

    async def test_dispatch_with_handler_returns_handler_result(self) -> None:
        bus = SimpleBus[str, str]().subscribe(str, _UpperHandler.factory)

        assert await bus.dispatch("hello") == "HELLO"

    async def test_dispatch_without_handler_returns_not_implemented(self) -> None:
        bus = SimpleBus[str, str]()

        assert await bus.dispatch("hello") is NotImplemented

    async def test_dispatch_with_failing_handler_raises_error(self) -> None:
        bus = SimpleBus[str, None]().subscribe(str, _FailingHandler.factory)

        with pytest.raises(ValueError, match="hello"):
            await bus.dispatch("hello")

    async def test_dispatch_with_failing_handler_and_fail_silently_returns_not_implemented(
        self,
    ) -> None:
        bus = SimpleBus[str, Any]().subscribe(
            str,
            _FailingHandler.factory,
            fail_silently=True,
        )

        assert await bus.dispatch("hello") is NotImplemented

    async def test_dispatch_with_listeners_calls_listeners(self) -> None:
        listened = []

        async def listener(message: str) -> None:
            listened.append(message)

        bus = SimpleBus[str, str]().add_listeners(listener, listener)
        await bus.dispatch("hello")

        assert listened == ["hello", "hello"]

    async def test_dispatch_with_middlewares_wraps_handler(self) -> None:
        results = []

        async def middleware(message: str) -> MiddlewareResult[str]:
            result = yield
            results.append(result)

        bus = (
            SimpleBus[str, str]()
            .subscribe(str, _UpperHandler.factory)
            .add_middlewares(middleware)
        )
        await bus.dispatch("hello")

        assert results == ["HELLO"]


class TestTaskBus:
    async def test_dispatch_with_several_handlers_calls_all_handlers(self) -> None:
        handled = []

        class FirstHandler:
            async def handle(self, message: str) -> None:
                handled.append(f"first {message}")

            @classmethod
            async def factory(cls) -> Self:
                return cls()

        class SecondHandler:
            async def handle(self, message: str) -> None:
                handled.append(f"second {message}")

            @classmethod
            async def factory(cls) -> Self:
                return cls()

        bus = (
            TaskBus[str]()
            .subscribe(str, FirstHandler.factory)
            .subscribe(str, SecondHandler.factory)
        )
        await bus.dispatch("hello")

        assert sorted(handled) == ["first hello", "second hello"]

    async def test_dispatch_without_handler(self) -> None:
        await TaskBus[str]().dispatch("hello")

    async def test_dispatch_with_failing_handler_raises_exception_group(
        self,
    ) -> None:
        bus = TaskBus[str]().subscribe(str, _FailingHandler.factory)

        with pytest.raises(ExceptionGroup) as exc_info:
            await bus.dispatch("hello")

        assert exc_info.group_contains(ValueError, match="hello")

    async def test_dispatch_with_failing_handler_and_fail_silently(self) -> None:
        bus = TaskBus[str]().subscribe(
            str,
            _FailingHandler.factory,
            fail_silently=True,
        )

        await bus.dispatch("hello")

    async def test_dispatch_with_listeners_calls_listeners(self) -> None:
        listened = []

        async def listener(message: str) -> None:
            listened.append(message)

        bus = TaskBus[str]().add_listeners(listener)
        await bus.dispatch("hello")

        assert listened == ["hello"]
