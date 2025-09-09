from collections.abc import Sequence
from typing import Any

import anyio

from cq import MiddlewareResult

__all__ = ("RetryMiddleware",)


class RetryMiddleware:
    __slots__ = ("__delay", "__exceptions", "__retry")

    __delay: float
    __exceptions: tuple[type[BaseException], ...]
    __retry: int

    def __init__(
        self,
        retry: int,
        delay: float = 0,
        exceptions: Sequence[type[BaseException]] = (Exception,),
    ) -> None:
        self.__delay = delay
        self.__exceptions = tuple(exceptions)
        self.__retry = retry

    async def __call__(self, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        retry = self.__retry

        for attempt in range(1, retry + 1):
            try:
                yield

            except self.__exceptions:
                if attempt == retry:
                    raise

            else:
                break

            await anyio.sleep(self.__delay)
