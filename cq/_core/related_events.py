from abc import abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import anyio
import injection
from anyio.abc import TaskGroup

from cq._core.message import Event, EventBus
from cq._core.scope import CQScope


@runtime_checkable
class RelatedEvents(Protocol):
    __slots__ = ()

    @abstractmethod
    def add(self, *events: Event) -> None:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class AnyIORelatedEvents(RelatedEvents):
    event_bus: EventBus
    task_group: TaskGroup
    history: list[Event] = field(default_factory=list, init=False)

    def __bool__(self) -> bool:  # pragma: no cover
        return bool(self.history)

    def add(self, *events: Event) -> None:
        self.history.extend(events)
        dispatch_method = self.event_bus.dispatch

        for event in events:
            self.task_group.start_soon(dispatch_method, event)


@injection.scoped(CQScope.TRANSACTION, mode="fallback")
async def related_events_recipe(event_bus: EventBus) -> AsyncIterator[RelatedEvents]:
    async with anyio.create_task_group() as task_group:
        yield AnyIORelatedEvents(event_bus, task_group)
