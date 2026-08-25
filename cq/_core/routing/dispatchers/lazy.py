from collections.abc import Awaitable, Callable
from types import GenericAlias
from typing import TypeAliasType

from cq._core.routing.di import DIAdapter
from cq._core.routing.dispatchers.abc import Dispatcher


class LazyDispatcher[I, O](Dispatcher[I, O]):
    __slots__ = ("__resolve",)

    __resolve: Callable[[], Awaitable[Dispatcher[I, O]]]

    def __init__(
        self,
        dispatcher_type: type[Dispatcher[I, O]] | TypeAliasType | GenericAlias,
        /,
        di: DIAdapter,
    ) -> None:
        self.__resolve = di.lazy(dispatcher_type)  # type: ignore[arg-type]

    async def dispatch(self, message: I, /) -> O:
        dispatcher = await self.__resolve()
        return await dispatcher.dispatch(message)
