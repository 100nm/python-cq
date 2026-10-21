import pytest

from cq._core.middleware import MiddlewareGroup
from cq.middlewares.exc import CaptureExceptionMiddleware


class _ErrorRecorder:
    def __init__(self) -> None:
        self.errors: list[tuple[type[Exception], str]] = []

    async def __call__(self, exc: Exception, message: str) -> None:
        self.errors.append((type(exc), message))


async def _failing_handler(message: str) -> str:
    raise ValueError(message)


class TestCaptureExceptionMiddleware:
    async def test_call_without_error_returns_handler_result(self) -> None:
        async def handler(message: str) -> str:
            return message.upper()

        on_error = _ErrorRecorder()
        middleware = CaptureExceptionMiddleware(on_error)
        group = MiddlewareGroup[[str], str]().add(middleware)

        assert await group.invoke(handler, "hello") == "HELLO"
        assert on_error.errors == []

    async def test_call_with_error_calls_on_error_and_returns_not_implemented(
        self,
    ) -> None:
        on_error = _ErrorRecorder()
        middleware = CaptureExceptionMiddleware(on_error)
        group = MiddlewareGroup[[str], str]().add(middleware)

        assert await group.invoke(_failing_handler, "hello") is NotImplemented
        assert on_error.errors == [(ValueError, "hello")]

    async def test_call_with_error_and_reraise_calls_on_error_and_raises_error(
        self,
    ) -> None:
        on_error = _ErrorRecorder()
        middleware = CaptureExceptionMiddleware(on_error, reraise=True)
        group = MiddlewareGroup[[str], str]().add(middleware)

        with pytest.raises(ValueError, match="hello"):
            await group.invoke(_failing_handler, "hello")

        assert on_error.errors == [(ValueError, "hello")]

    async def test_call_with_uncaptured_error_raises_error(self) -> None:
        on_error = _ErrorRecorder()
        middleware = CaptureExceptionMiddleware(on_error, exceptions=[KeyError])
        group = MiddlewareGroup[[str], str]().add(middleware)

        with pytest.raises(ValueError, match="hello"):
            await group.invoke(_failing_handler, "hello")

        assert on_error.errors == []

    async def test_sync_with_success_returns_middleware_calling_sync_on_error(
        self,
    ) -> None:
        errors = []

        def on_error(exc: Exception, message: str) -> None:
            errors.append((type(exc), message))

        middleware = CaptureExceptionMiddleware.sync(on_error)
        group = MiddlewareGroup[[str], str]().add(middleware)

        assert await group.invoke(_failing_handler, "hello") is NotImplemented
        assert errors == [(ValueError, "hello")]
