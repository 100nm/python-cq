from contextlib import suppress

from cq import ContextCommandPipeline, DIAdapter, Router

__all__ = (
    "command_handler",
    "event_handler",
    "new_command_bus",
    "new_event_bus",
    "new_query_bus",
    "query_handler",
    "router",
)


def __detect_di_adapter() -> DIAdapter | None:
    with suppress(ImportError):
        from .ext.injection import InjectionAdapter

        return InjectionAdapter()

    return None  # pragma: no cover


router = Router(__detect_di_adapter()).register_defaults()

command_handler = router.command_handler
event_handler = router.event_handler
query_handler = router.query_handler

new_command_bus = router.new_command_bus
new_event_bus = router.new_event_bus
new_query_bus = router.new_query_bus

ContextCommandPipeline._set_default_di(router.di)
