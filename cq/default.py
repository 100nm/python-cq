from contextlib import suppress

from ._core.routing.command_pipeline import ContextCommandPipeline
from ._core.routing.di import DIAdapter
from ._core.routing.router import Router

__all__ = (
    "__router__",
    "command_handler",
    "event_handler",
    "new_command_bus",
    "new_event_bus",
    "new_query_bus",
    "query_handler",
)


def __detect_di_adapter() -> DIAdapter | None:
    with suppress(ImportError):
        from .ext.injection import InjectionAdapter

        return InjectionAdapter()

    return None  # pragma: no cover


__router__ = Router(__detect_di_adapter()).register_defaults()

command_handler = __router__.command_handler
event_handler = __router__.event_handler
query_handler = __router__.query_handler

new_command_bus = __router__.new_command_bus
new_event_bus = __router__.new_event_bus
new_query_bus = __router__.new_query_bus

ContextCommandPipeline._set_default_di(__router__.di)
