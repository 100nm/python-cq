from cq import ContextCommandPipeline, Router


class _CreateCommand: ...


class _PublishCommand: ...


class _Created: ...


class _Published: ...


class _FindQuery: ...


class _Found: ...


class TestContextCommandPipeline:
    async def test_dispatch_with_query_step_dispatches_converted_message_as_query(
        self,
        router: Router,
    ) -> None:
        @router.command_handler
        class CreateHandler:
            async def handle(self, command: _CreateCommand) -> _Created:
                return _Created()

        @router.query_handler
        class FindHandler:
            async def handle(self, query: _FindQuery) -> _Found:
                return _Found()

        @router.command_handler
        class PublishHandler:
            async def handle(self, command: _PublishCommand) -> _Published:
                return _Published()

        class Context:
            created: _Created
            found: _Found

            pipeline: ContextCommandPipeline[_CreateCommand] = router.command_pipeline()

            @pipeline.query_step
            def _(self, created: _Created) -> _FindQuery:
                self.created = created
                return _FindQuery()

            @pipeline.step
            async def _(self, found: _Found) -> _PublishCommand:
                self.found = found
                return _PublishCommand()

        context = await Context.pipeline.dispatch(_CreateCommand())

        assert isinstance(context.created, _Created)
        assert isinstance(context.found, _Found)

    async def test_dispatch_with_static_query_step_dispatches_query(
        self,
        router: Router,
    ) -> None:
        queries = []

        @router.command_handler
        class CreateHandler:
            async def handle(self, command: _CreateCommand) -> None: ...

        @router.query_handler
        class FindHandler:
            async def handle(self, query: _FindQuery) -> None:
                queries.append(query)

        query = _FindQuery()

        class Context:
            pipeline: ContextCommandPipeline[_CreateCommand] = (
                router.command_pipeline().add_static_query_step(query)
            )

        await Context.pipeline.dispatch(_CreateCommand())

        assert queries == [query]
