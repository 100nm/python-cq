import asyncio
from abc import abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from inspect import isclass
from types import GenericAlias
from typing import Protocol, Self, TypeAliasType, runtime_checkable

import injection

from cq._core.dispatcher.base import BaseDispatcher, Dispatcher

type HandlerType[**P, T] = type[Handler[P, T]]
type HandlerFactory[**P, T] = Callable[..., Handler[P, T]]

type BusType[I, O] = type[Bus[I, O]]


@runtime_checkable
class Handler[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    async def handle(self, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError


@runtime_checkable
class Bus[I, O](Dispatcher[I, O], Protocol):
    __slots__ = ()

    @abstractmethod
    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        raise NotImplementedError


@dataclass(eq=False, frozen=True, slots=True)
class SubscriberDecorator[I, O]:
    bus_type: BusType[I, O] | TypeAliasType | GenericAlias
    injection_module: injection.Module = field(default_factory=injection.mod)

    def __call__(self, first_input_type: type[I], /, *input_types: type[I]):  # type: ignore[no-untyped-def]
        def decorator(wrapped):  # type: ignore[no-untyped-def]
            if not isclass(wrapped) or not issubclass(wrapped, Handler):
                raise TypeError(f"`{wrapped}` isn't a valid handler.")

            bus = self.__find_bus()
            factory = self.injection_module.make_injected_function(wrapped)

            for input_type in (first_input_type, *input_types):
                bus.subscribe(input_type, factory)

            return wrapped

        return decorator

    def __find_bus(self) -> Bus[I, O]:
        return self.injection_module.find_instance(self.bus_type)


class SimpleBus[I, O](BaseDispatcher[I, O], Bus[I, O]):
    __slots__ = ("__handlers",)

    __handlers: dict[type[I], HandlerFactory[[I], O]]

    def __init__(self) -> None:
        super().__init__()
        self.__handlers = {}

    async def dispatch(self, input_value: I, /) -> O:
        input_type = type(input_value)

        try:
            handler_factory = self.__handlers[input_type]
        except KeyError:
            return NotImplemented

        return await self._invoke_with_middlewares(
            handler_factory().handle,
            input_value,
        )

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        if input_type in self.__handlers:
            raise RuntimeError(
                f"A handler is already registered for the input type: `{input_type}`."
            )

        self.__handlers[input_type] = factory
        return self


class TaskBus[I](BaseDispatcher[I, None], Bus[I, None]):
    __slots__ = ("__handlers",)

    __handlers: dict[type[I], list[HandlerFactory[[I], None]]]

    def __init__(self) -> None:
        super().__init__()
        self.__handlers = defaultdict(list)

    async def dispatch(self, input_value: I, /) -> None:
        handler_factories = self.__handlers.get(type(input_value))

        if not handler_factories:
            return

        await asyncio.gather(
            *(
                self._invoke_with_middlewares(
                    handler_factory().handle,
                    input_value,
                )
                for handler_factory in handler_factories
            )
        )

    def subscribe(
        self,
        input_type: type[I],
        factory: HandlerFactory[[I], None],
    ) -> Self:
        self.__handlers[input_type].append(factory)
        return self
