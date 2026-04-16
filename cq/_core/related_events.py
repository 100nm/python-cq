from abc import abstractmethod
from dataclasses import dataclass, field
from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from anyio import create_task_group
from anyio.abc import TaskGroup

from cq._core.message import Event, EventBus


@runtime_checkable
class RelatedEvents(Protocol):
    __slots__ = ()

    @abstractmethod
    def add(self, *events: Event) -> None:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class AnyIORelatedEvents(RelatedEvents):
    event_bus: EventBus
    task_group: TaskGroup = field(default_factory=create_task_group)
    history: list[Event] = field(default_factory=list, init=False)

    def __bool__(self) -> bool:  # pragma: no cover
        return bool(self.history)

    async def __aenter__(self) -> Self:
        await self.task_group.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.task_group.__aexit__(None, None, None)

    def add(self, *events: Event) -> None:
        self.history.extend(events)
        dispatch_method = self.event_bus.dispatch

        for event in events:
            self.task_group.start_soon(dispatch_method, event)
