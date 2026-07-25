from ._core.cq import CQ
from ._core.di import DIAdapter
from ._core.di import NoDI as _NoDI
from ._core.dispatchers.abc import Dispatcher
from ._core.dispatchers.bus import Bus
from ._core.dispatchers.pipe import ContextPipeline, Pipe
from ._core.message import (
    AnyCommandBus,
    Command,
    CommandBus,
    Event,
    EventBus,
    Query,
    QueryBus,
)
from ._core.middleware import Middleware, MiddlewareResult, resolve_handler_source
from ._core.pipetools import ContextCommandPipeline as _ContextCommandPipeline
from ._core.pump import Pump
from ._core.queues.abc import Consumer, Delivery, Producer, Queue
from ._core.queues.memory import MemoryQueue
from ._core.related_events import AnyIORelatedEvents, RelatedEvents

__all__ = (
    "CQ",
    "AnyCommandBus",
    "AnyIORelatedEvents",
    "Bus",
    "Command",
    "CommandBus",
    "Consumer",
    "ContextCommandPipeline",
    "ContextPipeline",
    "DIAdapter",
    "Delivery",
    "Dispatcher",
    "Event",
    "EventBus",
    "MemoryQueue",
    "Middleware",
    "MiddlewareResult",
    "Pipe",
    "Producer",
    "Pump",
    "Query",
    "QueryBus",
    "Queue",
    "RelatedEvents",
    "__cq__",
    "command_handler",
    "event_handler",
    "new_command_bus",
    "new_event_bus",
    "new_query_bus",
    "query_handler",
    "resolve_handler_source",
)

try:
    from .ext.injection import InjectionAdapter as _InjectionAdapter

except ImportError:  # pragma: no cover
    __cq__ = CQ(_NoDI())

else:
    __cq__ = CQ(_InjectionAdapter())

__cq__.register_defaults()

command_handler = __cq__.command_handler
event_handler = __cq__.event_handler
query_handler = __cq__.query_handler

new_command_bus = __cq__.new_command_bus
new_event_bus = __cq__.new_event_bus
new_query_bus = __cq__.new_query_bus


class ContextCommandPipeline[C: Command](_ContextCommandPipeline[C]):
    __slots__ = ()

    def __init__(self, di: DIAdapter = __cq__.di) -> None:
        super().__init__(di)
