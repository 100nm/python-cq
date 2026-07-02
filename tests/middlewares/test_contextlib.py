from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Self

import pytest

from cq import Bus
from cq.middlewares.contextlib import (
    AsyncContextManagerMiddleware,
    ContextManagerMiddleware,
)


class TestAsyncContextManagerMiddleware:
    async def test_call_with_success(self, bus: Bus[Any, Any]) -> None:
        events: list[str] = []

        @asynccontextmanager
        async def context() -> AsyncIterator[None]:
            events.append("enter")
            try:
                yield
            finally:
                events.append("exit")

        class Handler:
            async def handle(self, message: str) -> None:
                events.append("handle")

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        bus.add_middlewares(AsyncContextManagerMiddleware(context()))
        bus.subscribe(str, Handler.async_factory)

        await bus.dispatch("Hello world!")
        assert events == ["enter", "handle", "exit"]

    async def test_call_with_handler_error_raise_value_error(
        self,
        bus: Bus[Any, Any],
    ) -> None:
        events: list[str] = []

        @asynccontextmanager
        async def context() -> AsyncIterator[None]:
            events.append("enter")
            try:
                yield
            finally:
                events.append("exit")

        class Handler:
            async def handle(self, message: str) -> None:
                raise ValueError(message)

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        bus.add_middlewares(AsyncContextManagerMiddleware(context()))
        bus.subscribe(str, Handler.async_factory)

        with pytest.raises(ValueError):
            await bus.dispatch("Hello world!")

        assert events == ["enter", "exit"]


class TestContextManagerMiddleware:
    async def test_call_with_success(self, bus: Bus[Any, Any]) -> None:
        events: list[str] = []

        @contextmanager
        def context() -> Iterator[None]:
            events.append("enter")
            try:
                yield
            finally:
                events.append("exit")

        class Handler:
            async def handle(self, message: str) -> None:
                events.append("handle")

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        bus.add_middlewares(ContextManagerMiddleware(context()))
        bus.subscribe(str, Handler.async_factory)

        await bus.dispatch("Hello world!")
        assert events == ["enter", "handle", "exit"]

    async def test_call_with_handler_error_raise_value_error(
        self,
        bus: Bus[Any, Any],
    ) -> None:
        events: list[str] = []

        @contextmanager
        def context() -> Iterator[None]:
            events.append("enter")
            try:
                yield
            finally:
                events.append("exit")

        class Handler:
            async def handle(self, message: str) -> None:
                raise ValueError(message)

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        bus.add_middlewares(ContextManagerMiddleware(context()))
        bus.subscribe(str, Handler.async_factory)

        with pytest.raises(ValueError):
            await bus.dispatch("Hello world!")

        assert events == ["enter", "exit"]
