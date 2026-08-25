from injection import Module

from cq import AnyCommandBus, RelatedEvents, Router
from tests.helpers.history import HistoryMiddleware


class TestCommandBus:
    async def test_dispatch_with_related_events(
        self,
        router: Router,
        history: HistoryMiddleware,
        injection_module: Module,
    ) -> None:
        class _Event: ...

        @router.event_handler
        class _EventHandler:
            async def handle(self, event: _Event) -> None: ...

        class _Command: ...

        @router.command_handler
        class _CommandHandler:
            def __init__(self, related_events: RelatedEvents) -> None:
                self.related_events = related_events

            async def handle(self, command: _Command) -> None:
                event = _Event()
                self.related_events.add(event)

        command_bus = injection_module.find_instance(AnyCommandBus)
        command = _Command()
        await command_bus.dispatch(command)

        assert len(history.records) == 2
        assert isinstance(history.records[0].args[0], _Event)
        assert isinstance(history.records[1].args[0], _Command)

    async def test_dispatch_with_fail_silently(
        self,
        router: Router,
        injection_module: Module,
    ) -> None:
        class _Command: ...

        @router.command_handler(fail_silently=True)
        class _CommandHandler:
            async def handle(self, command: _Command) -> None:
                raise ValueError

        command_bus = injection_module.find_instance(AnyCommandBus)
        assert await command_bus.dispatch(_Command()) is NotImplemented
