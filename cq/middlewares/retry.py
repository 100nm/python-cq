import asyncio
from typing import Any

from cq import MiddlewareResult

__all__ = ("RetryMiddleware",)


class RetryMiddleware:
    __slots__ = ("__delay", "__exceptions", "__retry")

    def __init__(
        self,
        retry: int,
        delay: float = 0,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        self.__delay = delay
        self.__exceptions = exceptions
        self.__retry = retry

    async def __call__(self, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        retry = self.__retry

        for attempt in range(1, retry + 1):
            try:
                yield

            except self.__exceptions as exc:
                if attempt == retry:
                    raise exc

            else:
                break

            await asyncio.sleep(self.__delay)
