from collections.abc import Awaitable
from types import GenericAlias
from typing import TypeAliasType

import injection

from cq._core.dispatcher.base import Dispatcher


class LazyDispatcher[I, O](Dispatcher[I, O]):
    __slots__ = ("__value",)

    __value: Awaitable[Dispatcher[I, O]]

    def __init__(
        self,
        dispatcher_type: type[Dispatcher[I, O]] | TypeAliasType | GenericAlias,
        /,
        *,
        injection_module: injection.Module | None = None,
        threadsafe: bool | None = None,
    ) -> None:
        module = injection_module or injection.mod()
        self.__value = module.aget_lazy_instance(dispatcher_type, threadsafe=threadsafe)

    async def dispatch(self, input_value: I, /) -> O:
        dispatcher = await self.__value
        return await dispatcher.dispatch(input_value)
