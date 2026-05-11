from cq import CQ, ContextCommandPipeline
from tests.helpers.history import HistoryMiddleware


class TestContextCommandPipeline:
    async def test_dispatch_with_success_return_any(
        self,
        cq: CQ,
        history: HistoryMiddleware,
    ) -> None:
        class Command0: ...

        class Command1: ...

        class Command2: ...

        class Query: ...

        class Foo: ...

        class Bar: ...

        class Baz: ...

        @cq.command_handler
        class CommandHandler0:
            async def handle(self, command: Command0) -> None:
                return

        @cq.command_handler
        class CommandHandler1:
            async def handle(self, command: Command1) -> Foo:
                return Foo()

        @cq.command_handler
        class CommandHandler2:
            async def handle(self, command: Command2) -> Bar:
                return Bar()

        @cq.query_handler
        class QueryHandler:
            async def handle(self, query: Query) -> Baz:
                return Baz()

        class Context:
            foo: Foo
            bar: Bar
            baz: Baz

            pipeline: ContextCommandPipeline[Command0] = ContextCommandPipeline(cq.di)

            pipeline.add_static_step(Command1())

            @pipeline.step
            def _(self, foo: Foo) -> Command2:
                self.foo = foo
                return Command2()

            @pipeline.query_step
            def _(self, bar: Bar) -> Query:
                self.bar = bar
                return Query()

            @pipeline.step
            async def _(self, baz: Baz) -> None:
                self.baz = baz

        cmd = Command0()
        ctx = await Context.pipeline(cmd)

        assert isinstance(ctx, Context)
        assert isinstance(ctx.foo, Foo)
        assert isinstance(ctx.bar, Bar)
        assert isinstance(ctx.baz, Baz)
        assert len(history.records) == 4
