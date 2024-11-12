from abc import ABC
from typing import Any

import injection

from cq._core.dispatcher.bus import Bus, SimpleBus, SubscriberDecorator, TaskBus
from cq._core.dto import DTO


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

injection.set_constant(SimpleBus(), CommandBus, alias=True)
injection.set_constant(TaskBus(), EventBus, alias=True)
injection.set_constant(SimpleBus(), QueryBus, alias=True)


@injection.inject
def get_command_bus[T](bus: CommandBus[T] = NotImplemented, /) -> CommandBus[T]:
    return bus


@injection.inject
def get_event_bus(bus: EventBus = NotImplemented, /) -> EventBus:
    return bus


@injection.inject
def get_query_bus[T](bus: QueryBus[T] = NotImplemented, /) -> QueryBus[T]:
    return bus
