from abc import ABC
from typing import Any

import injection

from cq._core.dispatcher.bus import Bus, SimpleBus, TaskBus
from cq._core.dto import DTO
from cq._core.handler import (
    HandlerDecorator,
    MultipleHandlerManager,
    SingleHandlerManager,
)
from cq._core.scope import CQScope
from cq.middlewares.scope import InjectionScopeMiddleware


class Message(DTO, ABC):
    __slots__ = ()


class Command(Message, ABC):
    __slots__ = ()


class Event(Message, ABC):
    __slots__ = ()


class Query(Message, ABC):
    __slots__ = ()


type CommandBus[T] = Bus[Command, T]
type EventBus = Bus[Event, None]
type QueryBus[T] = Bus[Query, T]

AnyCommandBus = CommandBus[Any]


command_handler: HandlerDecorator[Command, Any] = HandlerDecorator(
    SingleHandlerManager(),
)
event_handler: HandlerDecorator[Event, None] = HandlerDecorator(
    MultipleHandlerManager(),
)
query_handler: HandlerDecorator[Query, Any] = HandlerDecorator(
    SingleHandlerManager(),
)


@injection.singleton(
    on=CommandBus,
    ignore_type_hint=True,  # type: ignore[call-arg]
    inject=False,
    mode="fallback",
)
def new_command_bus[T]() -> CommandBus[T]:
    bus = SimpleBus(command_handler.manager)
    bus.add_middlewares(InjectionScopeMiddleware(CQScope.ON_COMMAND))
    return bus


@injection.singleton(
    inject=False,
    mode="fallback",
)
def new_event_bus() -> EventBus:
    return TaskBus(event_handler.manager)


@injection.singleton(
    on=QueryBus,
    ignore_type_hint=True,  # type: ignore[call-arg]
    inject=False,
    mode="fallback",
)
def new_query_bus[T]() -> QueryBus[T]:
    return SimpleBus(query_handler.manager)
