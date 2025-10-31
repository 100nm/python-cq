from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import BackgroundTasks, Depends
from injection.ext.fastapi import Inject

from cq import (
    Command,
    CommandBus,
    DeferredDispatcher,
    Dispatcher,
    Event,
    EventBus,
    Query,
    QueryBus,
)

__all__ = (
    "DeferredCommandBus",
    "DeferredEventBus",
    "DeferredQueryBus",
    "FastAPIDeferredDispatcher",
)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class FastAPIDeferredDispatcher[I](DeferredDispatcher[I]):
    background_tasks: BackgroundTasks
    dispatcher: Dispatcher[I, Any]

    async def defer(self, input_value: I, /) -> None:
        self.background_tasks.add_task(self.dispatcher.dispatch, input_value)


async def new_deferred_command_bus[T](
    background_tasks: BackgroundTasks,
    command_bus: Inject[CommandBus[T]],
) -> DeferredDispatcher[Command]:
    return FastAPIDeferredDispatcher(background_tasks, command_bus)


async def new_deferred_event_bus(
    background_tasks: BackgroundTasks,
    event_bus: Inject[EventBus],
) -> DeferredDispatcher[Event]:
    return FastAPIDeferredDispatcher(background_tasks, event_bus)


async def new_deferred_query_bus[T](
    background_tasks: BackgroundTasks,
    query_bus: Inject[QueryBus[T]],
) -> DeferredDispatcher[Query]:
    return FastAPIDeferredDispatcher(background_tasks, query_bus)


if TYPE_CHECKING:  # pragma: no cover
    type DeferredCommandBus = DeferredDispatcher[Command]
    type DeferredEventBus = DeferredDispatcher[Event]
    type DeferredQueryBus = DeferredDispatcher[Query]

else:
    DeferredCommandBus = Annotated[
        DeferredDispatcher[Command],
        Depends(new_deferred_command_bus, use_cache=False),
    ]
    DeferredEventBus = Annotated[
        DeferredDispatcher[Event],
        Depends(new_deferred_event_bus, use_cache=False),
    ]
    DeferredQueryBus = Annotated[
        DeferredDispatcher[Query],
        Depends(new_deferred_query_bus, use_cache=False),
    ]
