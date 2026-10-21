from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

import pytest

from cq._core.middleware import MiddlewareGroup
from cq.middlewares.contextlib import (
    AsyncContextManagerMiddleware,
    ContextManagerMiddleware,
)


class TestAsyncContextManagerMiddleware:
    async def test_call_with_success_enters_context_around_handler(self) -> None:
        calls = []

        @asynccontextmanager
        async def context() -> AsyncIterator[None]:
            calls.append("enter")
            yield
            calls.append("exit")

        async def handler() -> None:
            calls.append("handler")

        middleware = AsyncContextManagerMiddleware(context())
        await MiddlewareGroup[[], None]().add(middleware).invoke(handler)

        assert calls == ["enter", "handler", "exit"]

    async def test_call_with_handler_error_raises_error_inside_context(
        self,
    ) -> None:
        errors = []

        @asynccontextmanager
        async def context() -> AsyncIterator[None]:
            try:
                yield
            except ValueError as exc:
                errors.append(exc)
                raise

        async def handler() -> None:
            raise ValueError("handler failed")

        middleware = AsyncContextManagerMiddleware(context())
        group = MiddlewareGroup[[], None]().add(middleware)

        with pytest.raises(ValueError, match="handler failed") as exc_info:
            await group.invoke(handler)

        assert errors == [exc_info.value]


class TestContextManagerMiddleware:
    async def test_call_with_success_enters_context_around_handler(self) -> None:
        calls = []

        @contextmanager
        def context() -> Iterator[None]:
            calls.append("enter")
            yield
            calls.append("exit")

        async def handler() -> None:
            calls.append("handler")

        middleware = ContextManagerMiddleware(context())
        await MiddlewareGroup[[], None]().add(middleware).invoke(handler)

        assert calls == ["enter", "handler", "exit"]

    async def test_call_with_handler_error_raises_error_inside_context(
        self,
    ) -> None:
        errors = []

        @contextmanager
        def context() -> Iterator[None]:
            try:
                yield
            except ValueError as exc:
                errors.append(exc)
                raise

        async def handler() -> None:
            raise ValueError("handler failed")

        middleware = ContextManagerMiddleware(context())
        group = MiddlewareGroup[[], None]().add(middleware)

        with pytest.raises(ValueError, match="handler failed") as exc_info:
            await group.invoke(handler)

        assert errors == [exc_info.value]
