from typing import Any, NoReturn

import pytest

from cq._core.routing.handler import HandlerDecorator, SingleHandlerRegistry


class _Handler:
    async def handle(self, input_value: str) -> NoReturn:
        raise NotImplementedError


class TestHandlerDecorator:
    @pytest.fixture(scope="function")
    def handler_decorator(self) -> HandlerDecorator[Any, Any]:
        return HandlerDecorator(SingleHandlerRegistry())

    def test_call_with_success_return_wrapped_type(
        self,
        handler_decorator: HandlerDecorator[Any, Any],
    ) -> None:
        assert handler_decorator(_Handler) is _Handler

    def test_call_with_input_type_return_wrapped_type(
        self,
        handler_decorator: HandlerDecorator[Any, Any],
    ) -> None:
        assert handler_decorator(str)(_Handler) is _Handler

    def test_call_with_no_args_return_wrapped_type(
        self,
        handler_decorator: HandlerDecorator[Any, Any],
    ) -> None:
        assert handler_decorator()(_Handler) is _Handler

    def test_call_with_missing_input_type_annotation_raise_type_error(
        self,
        handler_decorator: HandlerDecorator[Any, Any],
    ) -> None:
        with pytest.raises(TypeError):

            @handler_decorator
            class Handler:
                async def handle(self, input_value): ...  # type: ignore[no-untyped-def]

    def test_call_with_missing_input_in_handle_raise_type_error(
        self,
        handler_decorator: HandlerDecorator[Any, Any],
    ) -> None:
        with pytest.raises(TypeError):

            @handler_decorator
            class Handler:
                async def handle(self): ...  # type: ignore[no-untyped-def]
