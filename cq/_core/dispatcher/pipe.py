from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import partial
from inspect import iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Protocol,
    Self,
    overload,
    runtime_checkable,
)

from cq._core.common.typing import Decorator, Method
from cq._core.dispatcher.base import BaseDispatcher, Dispatcher
from cq._core.middleware import Middleware, MiddlewareGroup

type ConvertAsync[**P, I, O] = Callable[Concatenate[O, P], Awaitable[I]]
type ConvertSync[**P, I, O] = Callable[Concatenate[O, P], I]
type Convert[**P, I, O] = ConvertAsync[P, I, O] | ConvertSync[P, I, O]

type ConvertMethodAsync[I, O] = Method[[O], Awaitable[I]]
type ConvertMethodSync[I, O] = Method[[O], I]
type ConvertMethod[I, O] = ConvertMethodAsync[I, O] | ConvertMethodSync[I, O]


@runtime_checkable
class PipelineConverter[**P, I, O](Protocol):
    __slots__ = ()

    @abstractmethod
    async def convert(self, output_value: O, /, *args: P.args, **kwargs: P.kwargs) -> I:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class PipelineStep[**P, I, O]:
    converter: PipelineConverter[P, I, O]
    dispatcher: Dispatcher[I, Any] | None = field(default=None)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class PipelineSteps[**P, I, O]:
    default_dispatcher: Dispatcher[Any, Any]
    __steps: list[PipelineStep[P, Any, Any]] = field(default_factory=list, init=False)

    def add[T](
        self,
        converter: PipelineConverter[P, T, Any],
        dispatcher: Dispatcher[T, Any] | None,
    ) -> Self:
        self.__steps.append(PipelineStep(converter, dispatcher))
        return self

    async def execute(self, input_value: I, /, *args: P.args, **kwargs: P.kwargs) -> O:
        dispatcher = self.default_dispatcher

        for step in self.__steps:
            output_value = await dispatcher.dispatch(input_value)
            input_value = await step.converter.convert(output_value, *args, **kwargs)

            if input_value is None:
                return NotImplemented

            dispatcher = step.dispatcher or self.default_dispatcher

        return await dispatcher.dispatch(input_value)


class Pipe[I, O](BaseDispatcher[I, O]):
    __slots__ = ("__steps",)

    __steps: PipelineSteps[[], I, O]

    def __init__(self, dispatcher: Dispatcher[Any, Any]) -> None:
        super().__init__()
        self.__steps = PipelineSteps(dispatcher)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def step[T](
            self,
            wrapped: ConvertAsync[[], T, Any],
            /,
            *,
            dispatcher: Dispatcher[T, Any] | None = ...,
        ) -> ConvertAsync[[], T, Any]: ...

        @overload
        def step[T](
            self,
            wrapped: ConvertSync[[], T, Any],
            /,
            *,
            dispatcher: Dispatcher[T, Any] | None = ...,
        ) -> ConvertSync[[], T, Any]: ...

        @overload
        def step(
            self,
            wrapped: None = ...,
            /,
            *,
            dispatcher: Dispatcher[Any, Any] | None = ...,
        ) -> Decorator: ...

    def step[T](
        self,
        wrapped: Convert[[], T, Any] | None = None,
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = None,
    ) -> Any:
        def decorator(wp: Convert[[], T, Any]) -> Convert[[], T, Any]:
            converter = (
                _AsyncPipelineConverter(wp)
                if iscoroutinefunction(wp)
                else _SyncPipelineConverter(wp)
            )
            self.__steps.add(converter, dispatcher)
            return wp

        return decorator(wrapped) if wrapped else decorator

    def add_static_step[T](
        self,
        input_value: T,
        *,
        dispatcher: Dispatcher[T, Any] | None = None,
    ) -> Self:
        converter = _StaticPipelineConverter(input_value)
        self.__steps.add(converter, dispatcher)
        return self

    async def dispatch(self, input_value: I, /) -> O:
        return await self._invoke_with_middlewares(self.__steps.execute, input_value)


class ContextPipeline[I]:
    __slots__ = ("__middleware_group", "__steps")

    __middleware_group: MiddlewareGroup[[I], Any]
    __steps: PipelineSteps[[object, type | None], I, Any]

    def __init__(self, dispatcher: Dispatcher[Any, Any]) -> None:
        self.__middleware_group = MiddlewareGroup()
        self.__steps = PipelineSteps(dispatcher)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __get__[Context](
            self,
            instance: None,
            owner: type[Context],
            /,
        ) -> Dispatcher[I, Context]: ...

        @overload
        def __get__[Context](
            self,
            instance: Context,
            owner: type[Context] | None = ...,
            /,
        ) -> Dispatcher[I, Context]: ...

        @overload
        def __get__(self, instance: None = ..., owner: None = ..., /) -> Self: ...

    def __get__[Context](
        self,
        instance: Context | None = None,
        owner: type[Context] | None = None,
        /,
    ) -> Self | Dispatcher[I, Context]:
        if instance is None:
            if owner is None:
                return self

            instance = owner()

        dispatch_method = partial(self.__execute, context=instance, context_type=owner)
        return BoundContextPipeline(dispatch_method)

    def add_middlewares(self, *middlewares: Middleware[[I], Any]) -> Self:
        self.__middleware_group.add(*middlewares)
        return self

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def step[T](
            self,
            wrapped: ConvertMethodAsync[T, Any],
            /,
            *,
            dispatcher: Dispatcher[T, Any] | None = ...,
        ) -> ConvertMethodAsync[T, Any]: ...

        @overload
        def step[T](
            self,
            wrapped: ConvertMethodSync[T, Any],
            /,
            *,
            dispatcher: Dispatcher[T, Any] | None = ...,
        ) -> ConvertMethodSync[T, Any]: ...

        @overload
        def step(
            self,
            wrapped: None = ...,
            /,
            *,
            dispatcher: Dispatcher[Any, Any] | None = ...,
        ) -> Decorator: ...

    def step[T](
        self,
        wrapped: ConvertMethod[T, Any] | None = None,
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = None,
    ) -> Any:
        def decorator(wp: ConvertMethod[T, Any]) -> ConvertMethod[T, Any]:
            converter = (
                _AsyncContextPipelineConverter(wp)
                if iscoroutinefunction(wp)
                else _SyncContextPipelineConverter(wp)
            )
            self.__steps.add(converter, dispatcher)
            return wp

        return decorator(wrapped) if wrapped else decorator

    async def __execute[Context](
        self,
        input_value: I,
        /,
        *,
        context: Context,
        context_type: type[Context] | None,
    ) -> Context:
        async def handler(i: I, /) -> Context:
            await self.__steps.execute(i, context, context_type)
            return context

        return await self.__middleware_group.invoke(handler, input_value)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class BoundContextPipeline[I, O](Dispatcher[I, O]):
    dispatch_method: Callable[[I], Awaitable[O]]

    async def dispatch(self, input_value: I, /) -> O:
        return await self.dispatch_method(input_value)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _AsyncPipelineConverter[**P, I, O](PipelineConverter[P, I, O]):
    converter: ConvertAsync[P, I, O]

    async def convert(self, output_value: O, /, *args: P.args, **kwargs: P.kwargs) -> I:
        return await self.converter(output_value, *args, **kwargs)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _SyncPipelineConverter[**P, I, O](PipelineConverter[P, I, O]):
    converter: ConvertSync[P, I, O]

    async def convert(self, output_value: O, /, *args: P.args, **kwargs: P.kwargs) -> I:
        return self.converter(output_value, *args, **kwargs)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _StaticPipelineConverter[I](PipelineConverter[..., I, Any]):
    input_value: I

    async def convert(self, output_value: Any, /, *args: Any, **kwargs: Any) -> I:
        return self.input_value


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _AsyncContextPipelineConverter[I, O](
    PipelineConverter[[object, type | None], I, O],
):
    converter: ConvertMethodAsync[I, O]

    async def convert(
        self,
        output_value: O,
        /,
        context: object,
        context_type: type | None,
    ) -> I:
        method = self.converter.__get__(context, context_type)
        return await method(output_value)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _SyncContextPipelineConverter[I, O](
    PipelineConverter[[object, type | None], I, O],
):
    converter: ConvertMethodSync[I, O]

    async def convert(
        self,
        output_value: O,
        /,
        context: object,
        context_type: type | None,
    ) -> I:
        method = self.converter.__get__(context, context_type)
        return method(output_value)
