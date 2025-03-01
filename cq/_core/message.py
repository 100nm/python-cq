from abc import ABC
from typing import Any

import injection

from cq._core.dispatcher.bus import Bus, SimpleBus, SubscriberDecorator, TaskBus
from cq._core.dto import DTO
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


command_handler: SubscriberDecorator[Command, Any] = SubscriberDecorator(CommandBus)
event_handler: SubscriberDecorator[Event, None] = SubscriberDecorator(EventBus)
query_handler: SubscriberDecorator[Query, Any] = SubscriberDecorator(QueryBus)


@injection.inject
def get_command_bus[T](bus: CommandBus[T] = NotImplemented, /) -> CommandBus[T]:
    return bus


def new_command_bus[T]() -> CommandBus[T]:
    bus: CommandBus[T] = SimpleBus()
    bus.add_middlewares(
        InjectionScopeMiddleware(CQScope.ON_COMMAND),
    )
    return bus


@injection.inject
def get_event_bus(bus: EventBus = NotImplemented, /) -> EventBus:
    return bus


def new_event_bus() -> EventBus:
    return TaskBus()


@injection.inject
def get_query_bus[T](bus: QueryBus[T] = NotImplemented, /) -> QueryBus[T]:
    return bus


def new_query_bus[T]() -> QueryBus[T]:
    return SimpleBus()


injection.set_constant(new_command_bus(), CommandBus, alias=True)
injection.set_constant(new_event_bus(), EventBus, alias=True)
injection.set_constant(new_query_bus(), QueryBus, alias=True)
