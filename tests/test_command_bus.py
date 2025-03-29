from injection import find_instance

from cq import AnyCommandBus, RelatedEvents, command_handler, event_handler
from tests.helpers.history import HistoryMiddleware


class TestCommandBus:
    async def test_dispatch_with_related_events(
        self,
        history: HistoryMiddleware,
    ) -> None:
        class _Event: ...

        @event_handler(_Event)
        class _EventHandler:
            async def handle(self, event: _Event) -> None: ...

        class _Command: ...

        @command_handler(_Command)
        class _CommandHandler:
            def __init__(self, related_events: RelatedEvents) -> None:
                self.related_events = related_events

            async def handle(self, command: _Command) -> None:
                event = _Event()
                self.related_events.add(event)

        command_bus = find_instance(AnyCommandBus)
        command = _Command()
        await command_bus.dispatch(command)

        assert len(history.records) == 2
        assert isinstance(history.records[0].args[0], _Event)
        assert isinstance(history.records[1].args[0], _Command)
