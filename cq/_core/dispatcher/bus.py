from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Iterator
from typing import Any, Protocol, Self, runtime_checkable

import anyio
from anyio.abc import TaskGroup

from cq._core.dispatcher.base import BaseDispatcher, Dispatcher
from cq._core.handler import (
    HandlerFactory,
    HandlerManager,
    MultipleHandlerManager,
    SingleHandlerManager,
)

type Listener[T] = Callable[[T], Awaitable[Any]]


@runtime_checkable
class Bus[I, O](Dispatcher[I, O], Protocol):
    __slots__ = ()

    @abstractmethod
    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def add_listeners(self, *listeners: Listener[I]) -> Self:
        raise NotImplementedError


class BaseBus[I, O](BaseDispatcher[I, O], Bus[I, O], ABC):
    __slots__ = ("__listeners", "__manager")

    __listeners: list[Listener[I]]
    __manager: HandlerManager[I, O]

    def __init__(self, manager: HandlerManager[I, O]) -> None:
        super().__init__()
        self.__listeners = []
        self.__manager = manager

    def add_listeners(self, *listeners: Listener[I]) -> Self:
        self.__listeners.extend(listeners)
        return self

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        self.__manager.subscribe(input_type, factory)
        return self

    def _handlers_from(
        self,
        input_type: type[I],
    ) -> Iterator[Callable[[I], Awaitable[O]]]:
        return self.__manager.handlers_from(input_type)

    def _trigger_listeners(self, input_value: I, /, task_group: TaskGroup) -> None:
        for listener in self.__listeners:
            task_group.start_soon(listener, input_value)


class SimpleBus[I, O](BaseBus[I, O]):
    __slots__ = ()

    def __init__(self, manager: HandlerManager[I, O] | None = None) -> None:
        super().__init__(manager or SingleHandlerManager())

    async def dispatch(self, input_value: I, /) -> O:
        async with anyio.create_task_group() as task_group:
            self._trigger_listeners(input_value, task_group)

        for handler in self._handlers_from(type(input_value)):
            return await self._invoke_with_middlewares(handler, input_value)

        return NotImplemented


class TaskBus[I](BaseBus[I, None]):
    __slots__ = ()

    def __init__(self, manager: HandlerManager[I, None] | None = None) -> None:
        super().__init__(manager or MultipleHandlerManager())

    async def dispatch(self, input_value: I, /) -> None:
        async with anyio.create_task_group() as task_group:
            self._trigger_listeners(input_value, task_group)

            for handler in self._handlers_from(type(input_value)):
                task_group.start_soon(
                    self._invoke_with_middlewares,
                    handler,
                    input_value,
                )
