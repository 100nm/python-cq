from abc import abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import anyio
import injection

from cq._core.message import Event, EventBus
from cq._core.scope import CQScope


@runtime_checkable
class RelatedEvents(Protocol):
    __slots__ = ()

    @abstractmethod
    def add(self, *events: Event) -> None:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SimpleRelatedEvents(RelatedEvents):
    items: list[Event] = field(default_factory=list)

    def add(self, *events: Event) -> None:
        self.items.extend(events)


@injection.scoped(CQScope.ON_COMMAND, mode="fallback")
async def related_events_recipe(event_bus: EventBus) -> AsyncIterator[RelatedEvents]:
    yield (instance := SimpleRelatedEvents())
    events = instance.items

    if not events:
        return

    async with anyio.create_task_group() as task_group:
        for event in events:
            task_group.start_soon(event_bus.dispatch, event)
