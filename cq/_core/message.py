from typing import Any

import injection

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


@injection.injectable(inject=False, mode="fallback")
def new_command_bus() -> CommandBus:  # type: ignore[type-arg]
    bus = SimpleBus(command_handler.manager)
    transaction_scope_middleware = InjectionScopeMiddleware(
        CQScope.TRANSACTION,
        exist_ok=True,
    )
    bus.add_middlewares(transaction_scope_middleware)
    return bus


@injection.injectable(inject=False, mode="fallback")
def new_event_bus() -> EventBus:
    return TaskBus(event_handler.manager)


@injection.injectable(inject=False, mode="fallback")
def new_query_bus() -> QueryBus:  # type: ignore[type-arg]
    return SimpleBus(query_handler.manager)
