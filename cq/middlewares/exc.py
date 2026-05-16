from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Concatenate, Self

from cq import MiddlewareResult

__all__ = ("CaptureExceptionMiddleware",)


class CaptureExceptionMiddleware[**P, Exc: BaseException]:
    __slots__ = ("__exceptions", "__on_error", "__reraise")

    __exceptions: tuple[type[Exc], ...]
    __on_error: Callable[Concatenate[Exc, P], Awaitable[Any]]
    __reraise: bool

    def __init__(
        self,
        on_error: Callable[Concatenate[Exc, P], Awaitable[Any]],
        /,
        exceptions: Sequence[type[Exc]] | None = None,
        reraise: bool = False,
    ) -> None:
        self.__exceptions = (Exception,) if exceptions is None else tuple(exceptions)  # type: ignore[assignment]
        self.__on_error = on_error
        self.__reraise = reraise

    async def __call__(
        self,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> MiddlewareResult[Any]:
        try:
            yield
        except self.__exceptions as exc:
            await self.__on_error(exc, *args, **kwargs)
            if self.__reraise:
                raise

    @classmethod
    def sync(
        cls,
        on_error: Callable[Concatenate[Exc, P], Any],
        /,
        exceptions: Sequence[type[Exc]] | None = None,
        reraise: bool = False,
    ) -> Self:
        async def async_on_error(
            exception: Exc,
            /,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> Any:
            return on_error(exception, *args, **kwargs)

        return cls(async_on_error, exceptions, reraise)
