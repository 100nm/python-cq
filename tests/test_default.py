from typing import ClassVar

from injection import mod

from cq import AnyCommandBus, Bus, ContextCommandPipeline
from cq.default import command_handler, new_command_bus


class _CreateCommand: ...


class _PublishCommand: ...


class _Published: ...


def test_import_with_injection_registers_buses_in_default_module() -> None:
    assert isinstance(mod().find_instance(AnyCommandBus), Bus)


async def test_new_command_bus_with_command_handler_returns_bus_dispatching_to_handler() -> (
    None
):
    @command_handler
    class Handler:
        async def handle(self, command: _CreateCommand) -> str:
            return "command handled"

    bus = new_command_bus()

    assert await bus.dispatch(_CreateCommand()) == "command handled"


async def test_context_command_pipeline_without_adapter_dispatches_through_default_router() -> (
    None
):
    @command_handler
    class Handler:
        async def handle(self, command: _PublishCommand) -> _Published:
            return _Published()

    class Context:
        published: _Published

        pipeline: ClassVar[ContextCommandPipeline[_PublishCommand]] = (
            ContextCommandPipeline()
        )

        @pipeline.step
        def _(self, published: _Published) -> None:
            self.published = published

    context = await Context.pipeline(_PublishCommand())

    assert isinstance(context.published, _Published)
