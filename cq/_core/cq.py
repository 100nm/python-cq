from typing import Any, Self

from cq._core.di import DIAdapter
from cq._core.dispatchers.bus import Bus, SimpleBus, TaskBus
from cq._core.handler import (
    HandlerDecorator,
    HandlerRegistry,
    MultipleHandlerRegistry,
    SingleHandlerRegistry,
)
from cq._core.message import Command, Event, Query
from cq._core.middlewares.scope import CommandDispatchScopeMiddleware


class CQ:
    __slots__ = ("__command_registry", "__di", "__event_registry", "__query_registry")

    __command_registry: HandlerRegistry[Command, Any]
    __di: DIAdapter
    __event_registry: HandlerRegistry[Event, Any]
    __query_registry: HandlerRegistry[Query, Any]

    def __init__(self, di: DIAdapter, /) -> None:
        self.__di = di
        self.__command_registry = SingleHandlerRegistry()
        self.__event_registry = MultipleHandlerRegistry()
        self.__query_registry = SingleHandlerRegistry()

    @property
    def di(self) -> DIAdapter:
        return self.__di

    @property
    def command_handler(self) -> HandlerDecorator[Command, Any]:
        return HandlerDecorator(self.__command_registry, self.__di)

    @property
    def event_handler(self) -> HandlerDecorator[Event, Any]:
        return HandlerDecorator(self.__event_registry, self.__di)

    @property
    def query_handler(self) -> HandlerDecorator[Query, Any]:
        return HandlerDecorator(self.__query_registry, self.__di)

    def new_command_bus(self) -> Bus[Command, Any]:
        bus = SimpleBus(self.__command_registry)
        command_middleware = CommandDispatchScopeMiddleware(self.__di)
        bus.add_middlewares(command_middleware)
        return bus

    def new_event_bus(self) -> Bus[Event, None]:
        return TaskBus(self.__event_registry)

    def new_query_bus(self) -> Bus[Query, Any]:
        return SimpleBus(self.__query_registry)

    def register_defaults(self) -> Self:
        self.__di.register_defaults(
            self.new_command_bus,
            self.new_event_bus,
            self.new_query_bus,
        )
        return self
