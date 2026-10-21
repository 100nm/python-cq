from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from typing import Any

import pytest

from cq import MiddlewareResult, resolve_handler_source
from cq._core.middleware import MiddlewareGroup
from cq._core.routing.dispatchers.bus import SimpleBus
from cq._core.routing.handler import HandlerDecorator, SingleHandlerRegistry
from cq.exceptions import MiddlewareError
from cq.middlewares.contextlib import ContextManagerMiddleware


class TestMiddlewareGroup:
    def test_add_with_success_returns_self(self) -> None:
        middleware = ContextManagerMiddleware(nullcontext())
        group = MiddlewareGroup[[], Any]()

        assert group.add(middleware) is group

    async def test_invoke_without_middlewares_returns_handler_result(self) -> None:
        async def handler(message: str) -> str:
            return message.upper()

        group = MiddlewareGroup[[str], str]()

        assert await group.invoke(handler, "hello") == "HELLO"

    async def test_invoke_with_generator_middleware_returns_handler_result(
        self,
    ) -> None:
        calls = []

        async def middleware(message: str) -> MiddlewareResult[str]:
            calls.append(f"before {message}")
            result = yield
            calls.append(f"after {result}")

        async def handler(message: str) -> str:
            calls.append("handler")
            return message.upper()

        group = MiddlewareGroup[[str], str]().add(middleware)
        result = await group.invoke(handler, "hello")

        assert result == "HELLO"
        assert calls == ["before hello", "handler", "after HELLO"]

    async def test_invoke_with_generator_method_middleware_returns_handler_result(
        self,
    ) -> None:
        class Middleware:
            def __init__(self) -> None:
                self.results: list[str] = []

            async def __call__(self, message: str) -> MiddlewareResult[str]:
                result = yield
                self.results.append(result)

        async def handler(message: str) -> str:
            return message.upper()

        middleware = Middleware()
        group = MiddlewareGroup[[str], str]().add(middleware)
        result = await group.invoke(handler, "hello")

        assert result == "HELLO"
        assert middleware.results == ["HELLO"]

    async def test_invoke_with_classic_middleware_returns_middleware_result(
        self,
    ) -> None:
        async def middleware(
            call_next: Callable[[str], Awaitable[str]],
            message: str,
        ) -> str:
            result = await call_next(message)
            return f"<{result}>"

        async def handler(message: str) -> str:
            return message.upper()

        group = MiddlewareGroup[[str], str]().add(middleware)

        assert await group.invoke(handler, "hello") == "<HELLO>"

    async def test_invoke_with_middlewares_added_in_one_call_runs_first_outermost(
        self,
    ) -> None:
        calls = []

        async def outer() -> MiddlewareResult[None]:
            calls.append("enter outer")
            yield
            calls.append("exit outer")

        async def inner() -> MiddlewareResult[None]:
            calls.append("enter inner")
            yield
            calls.append("exit inner")

        async def handler() -> None:
            calls.append("handler")

        group = MiddlewareGroup[[], None]().add(outer, inner)
        await group.invoke(handler)

        assert calls == [
            "enter outer",
            "enter inner",
            "handler",
            "exit inner",
            "exit outer",
        ]

    async def test_invoke_with_middlewares_added_in_several_calls_runs_last_outermost(
        self,
    ) -> None:
        calls = []

        async def inner() -> MiddlewareResult[None]:
            calls.append("enter inner")
            yield
            calls.append("exit inner")

        async def outer() -> MiddlewareResult[None]:
            calls.append("enter outer")
            yield
            calls.append("exit outer")

        async def handler() -> None:
            calls.append("handler")

        group = MiddlewareGroup[[], None]().add(inner).add(outer)
        await group.invoke(handler)

        assert calls == [
            "enter outer",
            "enter inner",
            "handler",
            "exit inner",
            "exit outer",
        ]

    async def test_invoke_with_handler_error_raises_error(self) -> None:
        errors = []

        async def middleware() -> MiddlewareResult[None]:
            try:
                yield
            except ValueError as exc:
                errors.append(exc)
                raise

        async def handler() -> None:
            raise ValueError("handler failed")

        group = MiddlewareGroup[[], None]().add(middleware)

        with pytest.raises(ValueError, match="handler failed") as exc_info:
            await group.invoke(handler)

        assert errors == [exc_info.value]

    async def test_invoke_with_middleware_suppressing_error_returns_not_implemented(
        self,
    ) -> None:
        async def middleware() -> MiddlewareResult[None]:
            try:
                yield
            except ValueError:
                return

        async def handler() -> None:
            raise ValueError

        group = MiddlewareGroup[[], Any]().add(middleware)

        assert await group.invoke(handler) is NotImplemented

    async def test_invoke_with_middleware_yielding_again_after_error_calls_handler_again(
        self,
    ) -> None:
        attempts: list[int] = []

        async def middleware() -> MiddlewareResult[str]:
            try:
                yield
            except ValueError:
                yield

        async def handler() -> str:
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                raise ValueError

            return "success"

        group = MiddlewareGroup[[], str]().add(middleware)

        assert await group.invoke(handler) == "success"
        assert attempts == [1, 2]

    async def test_invoke_with_middleware_not_yielding_returns_not_implemented(
        self,
    ) -> None:
        handled = []

        async def middleware(message: str) -> MiddlewareResult[None]:
            if message == "ignored":
                return

            yield

        async def handler(message: str) -> None:
            handled.append(message)

        group = MiddlewareGroup[[str], Any]().add(middleware)

        assert await group.invoke(handler, "ignored") is NotImplemented
        await group.invoke(handler, "kept")
        assert handled == ["kept"]

    async def test_invoke_with_middleware_yielding_twice_raises_middleware_error(
        self,
    ) -> None:
        async def middleware() -> MiddlewareResult[None]:
            yield
            yield

        async def handler() -> None: ...

        group = MiddlewareGroup[[], None]().add(middleware)

        with pytest.raises(MiddlewareError, match="Too many `yield` keywords"):
            await group.invoke(handler)


async def test_resolve_handler_source_with_success_returns_handler_type() -> None:
    registry = SingleHandlerRegistry[str, None]()

    @HandlerDecorator(registry)
    class Handler:
        async def handle(self, message: str) -> None: ...

    sources = []

    async def resolving_middleware(
        call_next: Callable[[str], Awaitable[None]],
        message: str,
    ) -> None:
        sources.append(resolve_handler_source(call_next))
        await call_next(message)

    async def other_middleware(message: str) -> MiddlewareResult[None]:
        yield

    bus = SimpleBus(registry)
    bus.add_middlewares(resolving_middleware, other_middleware)
    await bus.dispatch("hello")

    assert sources == [Handler]
