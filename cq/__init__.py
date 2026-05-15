from ._core.cq import CQ
from ._core.di import DIAdapter
from ._core.di import NoDI as _NoDI
from ._core.dispatcher.base import Dispatcher
from ._core.dispatcher.bus import Bus
from ._core.dispatcher.pipe import ContextPipeline, Pipe
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
from ._core.queue.base import Consumer, Producer, Queue
from ._core.queue.memory import MemoryQueue
from ._core.related_events import AnyIORelatedEvents, RelatedEvents

__all__ = (
    "AnyCommandBus",
    "AnyIORelatedEvents",
    "Bus",
    "CQ",
    "Command",
    "CommandBus",
    "Consumer",
    "ContextCommandPipeline",
    "ContextPipeline",
    "DIAdapter",
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
    "command_handler",
    "event_handler",
    "new_command_bus",
    "new_event_bus",
    "new_query_bus",
    "query_handler",
    "resolve_handler_source",
)

try:
    from cq.ext.injection import InjectionAdapter as _InjectionAdapter

except ImportError:  # pragma: no cover
    _default = CQ(_NoDI())

else:
    _default = CQ(_InjectionAdapter())

_default.register_defaults()

command_handler = _default.command_handler
event_handler = _default.event_handler
query_handler = _default.query_handler

new_command_bus = _default.new_command_bus
new_event_bus = _default.new_event_bus
new_query_bus = _default.new_query_bus


class ContextCommandPipeline[C: Command](_ContextCommandPipeline[C]):
    __slots__ = ()

    def __init__(self, di: DIAdapter = _default.di) -> None:
        super().__init__(di)


del _default
