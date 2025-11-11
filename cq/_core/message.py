from typing import Any, Final

import injection

from cq._core.dispatcher.base import Dispatcher
from cq._core.dispatcher.bus import Bus, SimpleBus, TaskBus
from cq._core.handler import (
    HandlerDecorator,
    MultipleHandlerManager,
    SingleHandlerManager,
)
from cq._core.scope import CQScope
from cq.middlewares.scope import InjectionScopeMiddleware

Command = object
Event = object
Query = object

type CommandBus[T] = Dispatcher[Command, T]
type EventBus = Dispatcher[Event, None]
type QueryBus[T] = Dispatcher[Query, T]

AnyCommandBus = CommandBus[Any]


command_handler: Final[HandlerDecorator[Command, Any]] = HandlerDecorator(
    SingleHandlerManager(),
)
event_handler: Final[HandlerDecorator[Event, None]] = HandlerDecorator(
    MultipleHandlerManager(),
)
query_handler: Final[HandlerDecorator[Query, Any]] = HandlerDecorator(
    SingleHandlerManager(),
)


def new_command_bus(*, threadsafe: bool | None = None) -> Bus[Command, Any]:
    bus = SimpleBus(command_handler.manager)
    transaction_scope_middleware = InjectionScopeMiddleware(
        CQScope.TRANSACTION,
        exist_ok=True,
        threadsafe=threadsafe,
    )
    bus.add_middlewares(transaction_scope_middleware)
    return bus


def new_event_bus() -> Bus[Event, None]:
    return TaskBus(event_handler.manager)


def new_query_bus() -> Bus[Query, Any]:
    return SimpleBus(query_handler.manager)


@injection.injectable(inject=False, mode="fallback")
def _() -> CommandBus:  # type: ignore[type-arg]
    return new_command_bus()


@injection.injectable(inject=False, mode="fallback")
def _() -> EventBus:
    return new_event_bus()


@injection.injectable(inject=False, mode="fallback")
def _() -> QueryBus:  # type: ignore[type-arg]
    return new_query_bus()


del _
