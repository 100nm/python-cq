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
from ._core.queuing.pump import Pump
from ._core.queuing.queues.abc import Consumer, Delivery, Producer, Queue
from ._core.queuing.queues.memory import MemoryQueue
from ._core.related_events import AnyIORelatedEvents, RelatedEvents
from ._core.routing.command_pipeline import (
    ContextCommandPipeline as _ContextCommandPipeline,
)
from ._core.routing.di import DIAdapter
from ._core.routing.dispatchers.abc import Dispatcher
from ._core.routing.dispatchers.bus import Bus
from ._core.routing.dispatchers.pipe import ContextPipeline, Pipe
from ._core.routing.router import Router

__all__ = (
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
    "Router",
    "__router__",
    "command_handler",
    "event_handler",
    "new_command_bus",
    "new_event_bus",
    "new_query_bus",
    "query_handler",
    "resolve_handler_source",
)


try:
    from .ext.injection import InjectionAdapter

except ImportError:  # pragma: no cover
    __router__ = Router()

else:
    __router__ = Router(InjectionAdapter())
    del InjectionAdapter

__router__.register_defaults()

command_handler = __router__.command_handler
event_handler = __router__.event_handler
query_handler = __router__.query_handler

new_command_bus = __router__.new_command_bus
new_event_bus = __router__.new_event_bus
new_query_bus = __router__.new_query_bus


class ContextCommandPipeline[C: Command](_ContextCommandPipeline[C]):
    __slots__ = ()

    def __init__(self, di: DIAdapter = __router__.di) -> None:
        super().__init__(di)
