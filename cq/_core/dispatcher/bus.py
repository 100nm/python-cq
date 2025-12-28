from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Iterator
from typing import Any, Protocol, Self, runtime_checkable

import anyio
from anyio.abc import TaskGroup

from cq._core.dispatcher.base import BaseDispatcher, Dispatcher
from cq._core.handler import (
    HandlerFactory,
    HandlerRegistry,
    MultipleHandlerRegistry,
    SingleHandlerRegistry,
)
from cq._core.middleware import Middleware

type Listener[T] = Callable[[T], Awaitable[Any]]


@runtime_checkable
class Bus[I, O](Dispatcher[I, O], Protocol):
    __slots__ = ()

    @abstractmethod
    def add_listeners(self, *listeners: Listener[I]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def add_middlewares(self, *middlewares: Middleware[[I], O]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        raise NotImplementedError


class BaseBus[I, O](BaseDispatcher[I, O], Bus[I, O], ABC):
    __slots__ = ("__listeners", "__registry")

    __listeners: list[Listener[I]]
    __registry: HandlerRegistry[I, O]

    def __init__(self, registry: HandlerRegistry[I, O], /) -> None:
        super().__init__()
        self.__listeners = []
        self.__registry = registry

    def add_listeners(self, *listeners: Listener[I]) -> Self:
        self.__listeners.extend(listeners)
        return self

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        self.__registry.subscribe(input_type, factory)
        return self

    def _handlers_from(
        self,
        input_type: type[I],
    ) -> Iterator[Callable[[I], Awaitable[O]]]:
        return self.__registry.handlers_from(input_type)

    def _trigger_listeners(self, input_value: I, /, task_group: TaskGroup) -> None:
        for listener in self.__listeners:
            task_group.start_soon(listener, input_value)


class SimpleBus[I, O](BaseBus[I, O]):
    __slots__ = ()

    def __init__(self, registry: HandlerRegistry[I, O] | None = None, /) -> None:
        super().__init__(registry or SingleHandlerRegistry())

    async def dispatch(self, input_value: I, /) -> O:
        async with anyio.create_task_group() as task_group:
            self._trigger_listeners(input_value, task_group)

        for handler in self._handlers_from(type(input_value)):
            return await self._invoke_with_middlewares(handler, input_value)

        return NotImplemented


class TaskBus[I](BaseBus[I, None]):
    __slots__ = ()

    def __init__(self, registry: HandlerRegistry[I, None] | None = None, /) -> None:
        super().__init__(registry or MultipleHandlerRegistry())

    async def dispatch(self, input_value: I, /) -> None:
        async with anyio.create_task_group() as task_group:
            self._trigger_listeners(input_value, task_group)

            for handler in self._handlers_from(type(input_value)):
                task_group.start_soon(
                    self._invoke_with_middlewares,
                    handler,
                    input_value,
                )
