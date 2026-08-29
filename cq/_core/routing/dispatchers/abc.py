from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Concatenate, Protocol, Self, runtime_checkable

from cq._core.middleware import Middleware, MiddlewareGroup


@runtime_checkable
class Dispatcher[I, O](Protocol):
    __slots__ = ()

    async def __call__(self, message: I, /) -> O:
        return await self.dispatch(message)

    @abstractmethod
    async def dispatch(self, message: I, /) -> O:
        raise NotImplementedError


class BaseDispatcher[I, O](Dispatcher[I, O], ABC):
    __slots__ = ("__middleware_group",)

    __middleware_group: MiddlewareGroup[Concatenate[I, ...], O]

    def __init__(self) -> None:
        self.__middleware_group = MiddlewareGroup()

    def add_middlewares(self, *middlewares: Middleware[Concatenate[I, ...], O]) -> Self:
        self.__middleware_group.add(*middlewares)
        return self

    async def _invoke(
        self,
        handler: Callable[Concatenate[I, ...], Awaitable[O]],
        message: I,
        /,
        fail_silently: bool = False,
    ) -> O:
        try:
            return await self.__middleware_group.invoke(handler, message)
        except Exception:
            if fail_silently:
                return NotImplemented

            raise
