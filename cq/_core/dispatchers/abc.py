from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Protocol, Self, runtime_checkable

from cq._core.middleware import Middleware, MiddlewareGroup, deliver_message


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

    __middleware_group: MiddlewareGroup[[I], O]

    def __init__(self) -> None:
        self.__middleware_group = MiddlewareGroup()

    def add_middlewares(self, *middlewares: Middleware[[I], O]) -> Self:
        self.__middleware_group.add(*middlewares)
        return self

    async def _deliver(
        self,
        message: I,
        handler: Callable[[I], Awaitable[O]],
        /,
        fail_silently: bool = False,
    ) -> O:
        return await deliver_message(
            message,
            handler,
            self.__middleware_group,
            fail_silently,
        )
