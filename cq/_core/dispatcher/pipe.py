from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, Self, overload

from cq._core.dispatcher.base import BaseDispatcher, Dispatcher
from cq._core.middleware import Middleware

type PipeConverter[I, O] = Callable[[O], Awaitable[I]]


class PipeConverterMethod[I, O](Protocol):
    def __get__(
        self,
        instance: object,
        owner: type | None = ...,
    ) -> PipeConverter[I, O]: ...


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class PipeStep[I, O]:
    converter: PipeConverter[I, O]
    dispatcher: Dispatcher[I, Any] | None = field(default=None)


class Pipe[I, O](BaseDispatcher[I, O]):
    __slots__ = ("__dispatcher", "__steps")

    __dispatcher: Dispatcher[Any, Any]
    __steps: list[PipeStep[Any, Any]]

    def __init__(self, dispatcher: Dispatcher[Any, Any]) -> None:
        super().__init__()
        self.__dispatcher = dispatcher
        self.__steps = []

    @overload
    def step[T](
        self,
        wrapped: PipeConverter[T, Any],
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = ...,
    ) -> PipeConverter[T, Any]: ...

    @overload
    def step[T](
        self,
        wrapped: None = ...,
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = ...,
    ) -> Callable[[PipeConverter[T, Any]], PipeConverter[T, Any]]: ...

    def step[T](
        self,
        wrapped: PipeConverter[T, Any] | None = None,
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = None,
    ) -> Any:
        def decorator(wp: PipeConverter[T, Any]) -> PipeConverter[T, Any]:
            step = PipeStep(wp, dispatcher)
            self.__steps.append(step)
            return wp

        return decorator(wrapped) if wrapped else decorator

    def add_static_step[T](
        self,
        input_value: T,
        *,
        dispatcher: Dispatcher[T, Any] | None = None,
    ) -> Self:
        @self.step(dispatcher=dispatcher)
        async def converter(_: Any) -> T:
            return input_value

        return self

    async def dispatch(self, input_value: I, /) -> O:
        return await self._invoke_with_middlewares(self.__execute, input_value)

    async def __execute(self, input_value: I) -> O:
        dispatcher = self.__dispatcher

        for step in self.__steps:
            output_value = await dispatcher.dispatch(input_value)
            input_value = await step.converter(output_value)

            if input_value is None:
                return NotImplemented

            dispatcher = step.dispatcher or self.__dispatcher

        return await dispatcher.dispatch(input_value)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ContextPipelineStep[I, O]:
    converter: PipeConverterMethod[I, O]
    dispatcher: Dispatcher[I, Any] | None = field(default=None)


class ContextPipeline[I]:
    __slots__ = ("__dispatcher", "__middlewares", "__steps")

    __dispatcher: Dispatcher[Any, Any]
    __middlewares: deque[Middleware[Any, Any]]
    __steps: list[ContextPipelineStep[Any, Any]]

    def __init__(self, dispatcher: Dispatcher[Any, Any]) -> None:
        self.__dispatcher = dispatcher
        self.__middlewares = deque()
        self.__steps = []

    @overload
    def __get__[O](
        self,
        instance: O,
        owner: type[O] | None = ...,
    ) -> Dispatcher[I, O]: ...

    @overload
    def __get__(self, instance: None = ..., owner: type | None = ...) -> Self: ...

    def __get__[O](
        self,
        instance: O | None = None,
        owner: type[O] | None = None,
    ) -> Self | Dispatcher[I, O]:
        if instance is None:
            return self

        pipeline = self.__new_pipeline(instance, owner)
        return BoundContextPipeline(instance, pipeline)

    def add_middlewares(self, *middlewares: Middleware[[I], Any]) -> Self:
        self.__middlewares.extendleft(reversed(middlewares))
        return self

    @overload
    def step[T](
        self,
        wrapped: PipeConverterMethod[T, Any],
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = ...,
    ) -> PipeConverterMethod[T, Any]: ...

    @overload
    def step[T](
        self,
        wrapped: None = ...,
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = ...,
    ) -> Callable[[PipeConverterMethod[T, Any]], PipeConverterMethod[T, Any]]: ...

    def step[T](
        self,
        wrapped: PipeConverterMethod[T, Any] | None = None,
        /,
        *,
        dispatcher: Dispatcher[T, Any] | None = None,
    ) -> Any:
        def decorator(wp: PipeConverterMethod[T, Any]) -> PipeConverterMethod[T, Any]:
            step = ContextPipelineStep(wp, dispatcher)
            self.__steps.append(step)
            return wp

        return decorator(wrapped) if wrapped else decorator

    def __new_pipeline[T](
        self,
        context: T,
        context_type: type[T] | None,
    ) -> Pipe[I, Any]:
        pipeline: Pipe[I, Any] = Pipe(self.__dispatcher)
        pipeline.add_middlewares(*self.__middlewares)

        for step in self.__steps:
            converter = step.converter.__get__(context, context_type)
            pipeline.step(converter, dispatcher=step.dispatcher)

        return pipeline


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class BoundContextPipeline[I, O](Dispatcher[I, O]):
    context: O
    pipeline: Pipe[I, Any]

    async def dispatch(self, input_value: I, /) -> O:
        await self.pipeline.dispatch(input_value)
        return self.context
