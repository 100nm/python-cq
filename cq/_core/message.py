from typing import Any

from cq._core.dispatchers.abc import Dispatcher

Command = object
Event = object
Query = object

type CommandBus[T] = Dispatcher[Command, T]
type EventBus = Dispatcher[Event, None]
type QueryBus[T] = Dispatcher[Query, T]

AnyCommandBus = CommandBus[Any]
