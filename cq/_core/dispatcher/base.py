import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Callable, Protocol, Self, runtime_checkable

from cq._core.middleware import Middleware, MiddlewareGroup


@runtime_checkable
class Dispatcher[I, O](Protocol):
    __slots__ = ()

    @abstractmethod
    async def dispatch(self, input_value: I, /) -> O:
        raise NotImplementedError

    @abstractmethod
    def dispatch_no_wait(self, *input_values: I) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_middlewares(self, *middlewares: Middleware[[I], O]) -> Self:
        raise NotImplementedError


class BaseDispatcher[I, O](Dispatcher[I, O], ABC):
    __slots__ = ("__middleware_group",)

    __middleware_group: MiddlewareGroup[[I], O]

    def __init__(self) -> None:
        self.__middleware_group = MiddlewareGroup()

    def dispatch_no_wait(self, *input_values: I) -> None:
        asyncio.gather(
            *(self.dispatch(input_value) for input_value in input_values),
            return_exceptions=True,
        )

    def add_middlewares(self, *middlewares: Middleware[[I], O]) -> Self:
        self.__middleware_group.add(*middlewares)
        return self

    async def _invoke_with_middlewares(
        self,
        handler: Callable[[I], Awaitable[O]],
        input_value: I,
        /,
    ) -> O:
        return await self.__middleware_group.invoke(handler, input_value)
