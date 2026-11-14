from typing import Any, Self

import pytest

from cq._core.routing.handler import (
    HandlerDecorator,
    HandlerEntry,
    MultipleHandlerRegistry,
    SingleHandlerRegistry,
)


class _Message: ...


class _ChildMessage(_Message): ...


class _OtherMessage: ...


class _Handler:
    async def handle(self, message: _Message) -> str:
        return "handled by _Handler"

    @classmethod
    async def factory(cls) -> Self:
        return cls()


class _UnannotatedHandler:
    async def handle(self, message): ...  # type: ignore[no-untyped-def]


class _ParameterlessHandler:
    async def handle(self) -> None: ...


class _NotHandler: ...


async def _handle(message: _Message) -> str:
    return "handled by _handle"


async def _other_handle(message: _Message) -> str:
    return "handled by _other_handle"


async def _unannotated_handle(message): ...  # type: ignore[no-untyped-def]


async def _parameterless_handle() -> None: ...


class TestHandlerEntry:
    async def test_call_with_factory_returns_handler_result(self) -> None:
        entry = HandlerEntry.from_factory(_Handler.factory)

        assert await entry(_Message()) == "handled by _Handler"

    async def test_call_with_function_returns_function_result(self) -> None:
        entry = HandlerEntry.from_function(_handle)

        assert await entry(_Message()) == "handled by _handle"

    def test_from_factory_with_source_returns_entry_with_source(self) -> None:
        entry = HandlerEntry.from_factory(_Handler.factory, _Handler)

        assert entry.source is _Handler

    def test_from_factory_without_source_returns_entry_with_unwrapped_factory(
        self,
    ) -> None:
        entry = HandlerEntry.from_factory(_Handler.factory)

        assert entry.source == _Handler.factory

    def test_from_function_with_success_returns_entry_with_function_as_source(
        self,
    ) -> None:
        entry = HandlerEntry.from_function(_handle)

        assert entry.source is _handle

    @pytest.mark.parametrize("fail_silently", [True, False])
    def test_from_function_with_fail_silently_returns_entry_with_fail_silently(
        self,
        fail_silently: bool,
    ) -> None:
        entry = HandlerEntry.from_function(_handle, fail_silently)

        assert entry.fail_silently is fail_silently


class TestMultipleHandlerRegistry:
    def test_subscribe_with_success_returns_self(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        entry = HandlerEntry.from_function(_handle)

        assert registry.subscribe(_Message, entry) is registry

    async def test_handlers_from_with_several_handlers_returns_all_handlers(
        self,
    ) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, HandlerEntry.from_function(_handle))
        registry.subscribe(_Message, HandlerEntry.from_function(_other_handle))

        results = [
            await entry(_Message()) for entry in registry.handlers_from(_Message)
        ]

        assert results == ["handled by _handle", "handled by _other_handle"]

    def test_handlers_from_with_subclass_returns_parent_handlers(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, HandlerEntry.from_function(_handle))

        entries = registry.handlers_from(_ChildMessage)

        assert [entry.source for entry in entries] == [_handle]

    def test_handlers_from_with_unknown_message_type_returns_nothing(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, HandlerEntry.from_function(_handle))

        assert list(registry.handlers_from(_OtherMessage)) == []

    def test_message_types_with_success_returns_subscribed_types(self) -> None:
        registry = MultipleHandlerRegistry[Any, str]()
        registry.subscribe(
            _Message | _OtherMessage,  # type: ignore[arg-type]
            HandlerEntry.from_function(_handle),
        )

        assert set(registry.message_types) == {_Message, _OtherMessage}


class TestSingleHandlerRegistry:
    def test_subscribe_with_success_returns_self(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        entry = HandlerEntry.from_function(_handle)

        assert registry.subscribe(_Message, entry) is registry

    def test_subscribe_with_subscribed_message_type_raises_runtime_error(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, HandlerEntry.from_function(_handle))
        entry = HandlerEntry.from_function(_other_handle)

        with pytest.raises(RuntimeError, match="A handler is already registered"):
            registry.subscribe(_Message, entry)

    def test_subscribe_with_union_containing_subscribed_type_raises_runtime_error(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, HandlerEntry.from_function(_handle))
        entry = HandlerEntry.from_function(_other_handle)

        with pytest.raises(RuntimeError):
            registry.subscribe(_OtherMessage | _Message, entry)  # type: ignore[arg-type]

        assert set(registry.message_types) == {_Message}

    def test_handlers_from_with_subclass_returns_parent_handler(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, HandlerEntry.from_function(_handle))

        entries = registry.handlers_from(_ChildMessage)

        assert [entry.source for entry in entries] == [_handle]

    def test_handlers_from_with_unknown_message_type_returns_nothing(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(_Message, HandlerEntry.from_function(_handle))

        assert list(registry.handlers_from(_OtherMessage)) == []

    def test_message_types_with_success_returns_subscribed_types(self) -> None:
        registry = SingleHandlerRegistry[Any, str]()
        registry.subscribe(
            _Message | _OtherMessage,  # type: ignore[arg-type]
            HandlerEntry.from_function(_handle),
        )

        assert set(registry.message_types) == {_Message, _OtherMessage}


class TestHandlerDecorator:
    @pytest.mark.parametrize("handler", [_Handler, _handle])
    def test_call_with_handler_subscribes_it_to_annotated_message_type(
        self,
        handler: Any,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        decorated = HandlerDecorator(registry)(handler)

        assert decorated is handler
        assert [entry.source for entry in registry.handlers_from(_Message)] == [handler]

    @pytest.mark.parametrize("handler", [_Handler, _handle])
    def test_call_with_message_type_subscribes_handler_to_message_type(
        self,
        handler: Any,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        decorated = HandlerDecorator(registry)(_OtherMessage)(handler)

        assert decorated is handler
        assert set(registry.message_types) == {_OtherMessage}

    @pytest.mark.parametrize("handler", [_Handler, _handle])
    def test_call_without_argument_subscribes_handler_to_annotated_message_type(
        self,
        handler: Any,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        decorated = HandlerDecorator(registry)()(handler)

        assert decorated is handler
        assert set(registry.message_types) == {_Message}

    @pytest.mark.parametrize("handler", [_Handler, _handle])
    @pytest.mark.parametrize("fail_silently", [True, False])
    def test_call_with_fail_silently_subscribes_handler_with_fail_silently(
        self,
        handler: Any,
        fail_silently: bool,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        HandlerDecorator(registry)(handler, fail_silently=fail_silently)

        entries = registry.handlers_from(_Message)
        assert [entry.fail_silently for entry in entries] == [fail_silently]

    @pytest.mark.parametrize(
        ("handler", "expected"),
        [
            (_Handler, "handled by _Handler"),
            (_handle, "handled by _handle"),
        ],
    )
    async def test_call_with_handler_subscribes_entry_returning_handler_result(
        self,
        handler: Any,
        expected: str,
    ) -> None:
        registry = SingleHandlerRegistry[Any, str]()

        HandlerDecorator(registry)(handler)

        results = [
            await entry(_Message()) for entry in registry.handlers_from(_Message)
        ]
        assert results == [expected]

    @pytest.mark.parametrize(
        "handler",
        [
            _UnannotatedHandler,
            _ParameterlessHandler,
            _unannotated_handle,
            _parameterless_handle,
        ],
    )
    def test_call_with_unresolvable_message_type_raises_type_error(
        self,
        handler: Any,
    ) -> None:
        handler_decorator = HandlerDecorator(SingleHandlerRegistry[Any, Any]())

        with pytest.raises(TypeError, match="Unable to resolve message type"):
            handler_decorator(handler)

    def test_call_with_message_type_and_not_handler_raises_type_error(
        self,
    ) -> None:
        registry = SingleHandlerRegistry[Any, Any]()
        decorator = HandlerDecorator(registry)(_Message)

        with pytest.raises(TypeError, match="isn't a handler"):
            decorator(_NotHandler)

        assert list(registry.message_types) == []
