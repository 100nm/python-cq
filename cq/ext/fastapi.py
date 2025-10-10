from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends
from injection.ext.fastapi import Inject

from cq import Bus, Command, CommandBus, DeferredBus, Event, EventBus, Query, QueryBus

__all__ = ("DeferredCommandBus", "DeferredEventBus", "DeferredQueryBus")


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class FastAPIDeferredBus[I](DeferredBus[I]):
    background_tasks: BackgroundTasks
    bus: Bus[I, Any]

    async def defer(self, input_value: I, /) -> None:
        self.background_tasks.add_task(self.bus.dispatch, input_value)


async def new_deferred_command_bus[T](
    background_tasks: BackgroundTasks,
    command_bus: Inject[CommandBus[T]],
) -> DeferredBus[Command]:
    return FastAPIDeferredBus(background_tasks, command_bus)


async def new_deferred_event_bus(
    background_tasks: BackgroundTasks,
    event_bus: Inject[EventBus],
) -> DeferredBus[Event]:
    return FastAPIDeferredBus(background_tasks, event_bus)


async def new_deferred_query_bus[T](
    background_tasks: BackgroundTasks,
    query_bus: Inject[QueryBus[T]],
) -> DeferredBus[Query]:
    return FastAPIDeferredBus(background_tasks, query_bus)


DeferredCommandBus = Annotated[DeferredBus[Command], Depends(new_deferred_command_bus)]
DeferredEventBus = Annotated[DeferredBus[Event], Depends(new_deferred_event_bus)]
DeferredQueryBus = Annotated[DeferredBus[Query], Depends(new_deferred_query_bus)]
