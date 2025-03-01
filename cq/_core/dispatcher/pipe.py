from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Self

from cq._core.dispatcher.base import BaseDispatcher, Dispatcher

type PipeConverter[I, O] = Callable[[O], Awaitable[I]]


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
            dispatcher = step.dispatcher or self.__dispatcher

        return await dispatcher.dispatch(input_value)
