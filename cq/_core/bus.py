import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from inspect import isclass
from types import GenericAlias
from typing import Protocol, Self, TypeAliasType, runtime_checkable

import injection

from cq._core.middleware import Middleware, MiddlewareGroup

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
class Bus[I, O](Protocol):
    __slots__ = ()

    @abstractmethod
    async def dispatch(self, input_value: I, /) -> O:
        raise NotImplementedError

    def dispatch_no_wait(self, first_input_value: I, /, *input_values: I) -> None:
        asyncio.gather(
            *(
                self.dispatch(input_value)
                for input_value in (first_input_value, *input_values)
            ),
            return_exceptions=True,
        )

    @abstractmethod
    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def add_middlewares(self, *middlewares: Middleware[[I], O]) -> Self:
        raise NotImplementedError


@dataclass(eq=False, frozen=True, slots=True)
class SubscriberDecorator[I, O]:
    bus_type: BusType[I, O] | TypeAliasType | GenericAlias
    injection_module: injection.Module = field(default_factory=injection.mod)

    def __call__[T](
        self,
        first_input_type: type[I],
        /,
        *input_types: type[I],
    ) -> Callable[[T], T]:
        def decorator(wrapped: T) -> T:
            if not isclass(wrapped) or not issubclass(wrapped, Handler):
                raise TypeError(f"`{wrapped}` isn't a valid handler.")

            bus = self.__find_bus()
            factory = self.injection_module.make_injected_function(wrapped)

            for input_type in (first_input_type, *input_types):
                bus.subscribe(input_type, factory)

            return wrapped  # type: ignore[return-value]

        return decorator

    def __find_bus(self) -> Bus[I, O]:
        return self.injection_module.find_instance(self.bus_type)


class _BaseBus[I, O](Bus[I, O], ABC):
    __slots__ = ("__middleware_group",)

    __middleware_group: MiddlewareGroup[[I], O]

    def __init__(self) -> None:
        self.__middleware_group = MiddlewareGroup()

    def add_middlewares(self, *middlewares: Middleware[[I], O]) -> Self:
        self.__middleware_group.add(*middlewares)
        return self

    async def _invoke(self, handler: Handler[[I], O], input_value: I, /) -> O:
        return await self.__middleware_group.invoke(handler.handle, input_value)


class SimpleBus[I, O](_BaseBus[I, O]):
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

        return await self._invoke(handler_factory(), input_value)

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        if input_type in self.__handlers:
            raise RuntimeError(
                f"A handler is already registered for the input type: `{input_type}`."
            )

        self.__handlers[input_type] = factory
        return self


class TaskBus[I](_BaseBus[I, None]):
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
                self._invoke(handler_factory(), input_value)
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
