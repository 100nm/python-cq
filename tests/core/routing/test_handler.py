from typing import Any, Self

import pytest

from cq._core.routing.handler import (
    HandleFunction,
    HandlerDecorator,
    MultipleHandlerRegistry,
    SingleHandlerRegistry,
)


class _Message: ...


class _ChildMessage(_Message): ...


class _OtherMessage: ...


class _Handler:
    async def handle(self, message: _Message) -> str:
        return f"handled by {type(self).__name__}"

    @classmethod
    async def factory(cls) -> Self:
        return cls()


class _OtherHandler(_Handler): ...


class _UnannotatedHandler:
    async def handle(self, message): ...  # type: ignore[no-untyped-def]


class _ParameterlessHandler:
    async def handle(self) -> None: ...


class TestHandleFunction:
    async def test_call_with_success_returns_handler_result(self) -> None:
        function = HandleFunction.create(_Handler.factory)

        assert await function(_Message()) == "handled by _Handler"

    def test_create_with_source_returns_function_with_source(self) -> None:
        function = HandleFunction.create(_Handler.factory, _Handler)

        assert function.source is _Handler

    def test_create_without_source_returns_function_with_unwrapped_factory(
        self,
    ) -> None:
        function = HandleFunction.create(_Handler.factory)

        assert function.source == _Handler.factory


class TestMultipleHandlerRegistry:
    def test_subscribe_with_success_returns_self(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()

        assert registry.subscribe(_Message, _Handler.factory) is registry

    async def test_handlers_from_with_several_handlers_returns_all_handlers(
        self,
    ) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, _Handler.factory)
        registry.subscribe(_Message, _OtherHandler.factory)

        results = [
            await function(_Message()) for function in registry.handlers_from(_Message)
        ]

        assert results == ["handled by _Handler", "handled by _OtherHandler"]

    def test_handlers_from_with_subclass_returns_parent_handlers(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, _Handler.factory, _Handler)

        functions = registry.handlers_from(_ChildMessage)

        assert [function.source for function in functions] == [_Handler]

    def test_handlers_from_with_unknown_message_type_returns_nothing(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, _Handler.factory)

        assert list(registry.handlers_from(_OtherMessage)) == []

    def test_message_types_with_success_returns_subscribed_types(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(_Message | _OtherMessage, _Handler.factory)  # type: ignore[arg-type]

        assert set(registry.message_types) == {_Message, _OtherMessage}


class TestSingleHandlerRegistry:
    def test_subscribe_with_success_returns_self(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        assert registry.subscribe(_Message, _Handler.factory) is registry

    def test_subscribe_with_subscribed_message_type_raises_runtime_error(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, _Handler.factory)

        with pytest.raises(RuntimeError, match="A handler is already registered"):
            registry.subscribe(_Message, _OtherHandler.factory)

    def test_subscribe_with_union_containing_subscribed_type_raises_runtime_error(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, _Handler.factory)

        with pytest.raises(RuntimeError):
            registry.subscribe(_OtherMessage | _Message, _OtherHandler.factory)  # type: ignore[arg-type]

        assert set(registry.message_types) == {_Message}

    def test_handlers_from_with_subclass_returns_parent_handler(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, _Handler.factory, _Handler)

        functions = registry.handlers_from(_ChildMessage)

        assert [function.source for function in functions] == [_Handler]

    def test_handlers_from_with_unknown_message_type_returns_nothing(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, _Handler.factory)

        assert list(registry.handlers_from(_OtherMessage)) == []

    def test_message_types_with_success_returns_subscribed_types(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message | _OtherMessage, _Handler.factory)  # type: ignore[arg-type]

        assert set(registry.message_types) == {_Message, _OtherMessage}


class TestHandlerDecorator:
    def test_call_with_handler_type_subscribes_it_to_annotated_message_type(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        handler_type = HandlerDecorator(registry)(_Handler)

        assert handler_type is _Handler
        assert [f.source for f in registry.handlers_from(_Message)] == [_Handler]

    def test_call_with_message_type_subscribes_handler_to_message_type(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        handler_type = HandlerDecorator(registry)(_OtherMessage)(_Handler)

        assert handler_type is _Handler
        assert set(registry.message_types) == {_OtherMessage}

    def test_call_without_argument_subscribes_handler_to_annotated_message_type(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        handler_type = HandlerDecorator(registry)()(_Handler)

        assert handler_type is _Handler
        assert set(registry.message_types) == {_Message}

    @pytest.mark.parametrize("fail_silently", [True, False])
    def test_call_with_fail_silently_subscribes_handler_with_fail_silently(
        self,
        fail_silently: bool,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        HandlerDecorator(registry)(_Handler, fail_silently=fail_silently)

        functions = registry.handlers_from(_Message)
        assert [f.fail_silently for f in functions] == [fail_silently]

    @pytest.mark.parametrize(
        "handler_type",
        [_UnannotatedHandler, _ParameterlessHandler],
    )
    def test_call_with_unresolvable_message_type_raises_type_error(
        self,
        handler_type: type,
    ) -> None:
        handler_decorator = HandlerDecorator(SingleHandlerRegistry[Any, Any]())

        with pytest.raises(TypeError, match="Unable to resolve message type"):
            handler_decorator(handler_type)
