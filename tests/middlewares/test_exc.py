from typing import Any, Self

import anyio
import pytest

from cq import Bus
from cq.middlewares.exc import CaptureExceptionMiddleware


class TestCaptureExceptionMiddleware:
    async def test_capture_exception_middleware_with_success(
        self,
        bus: Bus[Any, Any],
    ) -> None:
        class Handler:
            async def handle(self, message: str) -> str:
                raise Exception  # noqa: TRY002

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        captured = anyio.Event()

        def capture(exc: Exception, message: str) -> None:
            captured.set()

        bus.add_middlewares(CaptureExceptionMiddleware.sync(capture))
        bus.subscribe(str, Handler.async_factory)

        assert not captured.is_set()
        await bus.dispatch("Hello world!")
        assert captured.is_set()

    async def test_capture_exception_middleware_with_reraise(
        self,
        bus: Bus[Any, Any],
    ) -> None:
        class Handler:
            async def handle(self, message: str) -> str:
                raise Exception  # noqa: TRY002

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        captured = anyio.Event()

        def capture(exc: Exception, message: str) -> None:
            captured.set()

        bus.add_middlewares(CaptureExceptionMiddleware.sync(capture, reraise=True))
        bus.subscribe(str, Handler.async_factory)

        assert not captured.is_set()

        with pytest.raises(Exception):  # noqa: B017
            await bus.dispatch("Hello world!")

        assert captured.is_set()
