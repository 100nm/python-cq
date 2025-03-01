from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from inspect import getmro, isclass
from types import GenericAlias
from typing import Any, Protocol, Self, TypeAliasType, runtime_checkable

import anyio
import injection

from cq._core.dispatcher.base import BaseDispatcher, Dispatcher

type HandlerType[**P, T] = type[Handler[P, T]]
type HandlerFactory[**P, T] = Callable[..., Awaitable[Handler[P, T]]]

type Listener[T] = Callable[[T], Awaitable[Any]]

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

    @abstractmethod
    def add_listeners(self, *listeners: Listener[I]) -> Self:
        raise NotImplementedError


@dataclass(eq=False, frozen=True, slots=True)
class SubscriberDecorator[I, O]:
    bus_type: BusType[I, O] | TypeAliasType | GenericAlias
    injection_module: injection.Module = field(default_factory=injection.mod)

    def __call__(self, first_input_type: type[I], /, *input_types: type[I]) -> Any:
        def decorator(wrapped: type[Handler[[I], O]]) -> type[Handler[[I], O]]:
            if not isclass(wrapped) or not issubclass(wrapped, Handler):
                raise TypeError(f"`{wrapped}` isn't a valid handler.")

            bus = self.injection_module.find_instance(self.bus_type)
            factory = self.injection_module.make_async_factory(wrapped)

            for input_type in (first_input_type, *input_types):
                bus.subscribe(input_type, factory)

            return wrapped

        return decorator


class BaseBus[I, O](BaseDispatcher[I, O], Bus[I, O], ABC):
    __slots__ = ("__listeners",)

    __listeners: list[Listener[I]]

    def __init__(self) -> None:
        super().__init__()
        self.__listeners = []

    def add_listeners(self, *listeners: Listener[I]) -> Self:
        self.__listeners.extend(listeners)
        return self

    async def _trigger_listeners(self, input_value: I, /) -> None:
        listeners = self.__listeners

        if not listeners:
            return

        async with anyio.create_task_group() as task_group:
            for listener in listeners:
                task_group.start_soon(listener, input_value)

    @staticmethod
    def _make_handle_function(
        handler_factory: HandlerFactory[[I], O],
    ) -> Callable[[I], Awaitable[O]]:
        async def handle(input_value: I) -> O:
            handler = await handler_factory()
            return await handler.handle(input_value)

        return handle


class SimpleBus[I, O](BaseBus[I, O]):
    __slots__ = ("__handlers",)

    __handlers: dict[type[I], HandlerFactory[[I], O]]

    def __init__(self) -> None:
        super().__init__()
        self.__handlers = {}

    async def dispatch(self, input_value: I, /) -> O:
        await self._trigger_listeners(input_value)

        for input_type in getmro(type(input_value)):
            if handler_factory := self.__handlers.get(input_type):
                break

        else:
            return NotImplemented

        handler = self._make_handle_function(handler_factory)
        return await self._invoke_with_middlewares(handler, input_value)

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        if input_type in self.__handlers:
            raise RuntimeError(
                f"A handler is already registered for the input type: `{input_type}`."
            )

        self.__handlers[input_type] = factory
        return self


class TaskBus[I](BaseBus[I, None]):
    __slots__ = ("__handlers",)

    __handlers: dict[type[I], list[HandlerFactory[[I], None]]]

    def __init__(self) -> None:
        super().__init__()
        self.__handlers = defaultdict(list)

    async def dispatch(self, input_value: I, /) -> None:
        await self._trigger_listeners(input_value)

        for input_type in getmro(type(input_value)):
            if handler_factories := self.__handlers.get(input_type):
                break

        else:
            return

        async with anyio.create_task_group() as task_group:
            for handler_factory in handler_factories:
                handler = self._make_handle_function(handler_factory)
                task_group.start_soon(
                    self._invoke_with_middlewares,
                    handler,
                    input_value,
                )

    def subscribe(
        self,
        input_type: type[I],
        factory: HandlerFactory[[I], None],
    ) -> Self:
        self.__handlers[input_type].append(factory)
        return self
