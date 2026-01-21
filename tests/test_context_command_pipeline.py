from cq import ContextCommandPipeline, command_handler, query_handler
from tests.helpers.history import HistoryMiddleware


class TestContextCommandPipeline:
    async def test_dispatch_with_success_return_any(
        self,
        history: HistoryMiddleware,
    ) -> None:
        class Command1: ...

        class Command2: ...

        class Query: ...

        class Foo: ...

        class Bar: ...

        class Baz: ...

        @command_handler
        class CommandHandler1:
            async def handle(self, command: Command1) -> Foo:
                return Foo()

        @command_handler
        class CommandHandler2:
            async def handle(self, command: Command2) -> Bar:
                return Bar()

        @query_handler
        class QueryHandler:
            async def handle(self, query: Query) -> Baz:
                return Baz()

        class Context:
            foo: Foo
            bar: Bar
            baz: Baz

            pipeline: ContextCommandPipeline[Command1] = ContextCommandPipeline()

            @pipeline.step
            async def _(self, foo: Foo) -> Command2:
                self.foo = foo
                return Command2()

            @pipeline.query_step
            async def _(self, bar: Bar) -> Query:
                self.bar = bar
                return Query()

            @pipeline.step
            async def _(self, baz: Baz) -> None:
                self.baz = baz

        cmd = Command1()
        ctx = await Context.pipeline.dispatch(cmd)

        assert isinstance(ctx, Context)
        assert isinstance(ctx.foo, Foo)
        assert isinstance(ctx.bar, Bar)
        assert isinstance(ctx.baz, Baz)
        assert len(history.records) == 3
