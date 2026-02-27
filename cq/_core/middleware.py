from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from inspect import isasyncgenfunction
from typing import Any, Concatenate, Self, TypeGuard

from cq._core.handler import HandleFunction, HandlerType
from cq.exceptions import MiddlewareError

type MiddlewareResult[T] = AsyncGenerator[None, T]
type GeneratorMiddleware[**P, T] = Callable[P, MiddlewareResult[T]]
type ClassicMiddleware[**P, T] = Callable[
    Concatenate[Callable[P, Awaitable[T]], P], Awaitable[T]
]

type Middleware[**P, T] = ClassicMiddleware[P, T] | GeneratorMiddleware[P, T]


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class MiddlewareGroup[**P, T]:
    __middlewares: list[ClassicMiddleware[P, T]] = field(
        default_factory=list,
        init=False,
    )

    def add(self, *middlewares: Middleware[P, T]) -> Self:
        classic_middlewares = reversed(
            tuple(self.__normalize(middleware) for middleware in middlewares)
        )
        self.__middlewares.extend(classic_middlewares)
        return self

    async def invoke(
        self,
        handler: Callable[P, Awaitable[T]],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        return await self.__apply_stack(handler)(*args, **kwargs)

    def __apply_stack(
        self,
        handler: Callable[P, Awaitable[T]],
    ) -> Callable[P, Awaitable[T]]:
        for middleware in self.__middlewares:
            handler = _BoundMiddleware(handler, middleware)

        return handler

    @staticmethod
    def __normalize(middleware: Middleware[P, T]) -> ClassicMiddleware[P, T]:
        if _is_gen_middleware(middleware):
            return _GeneratorMiddleware(middleware)

        return middleware  # type: ignore[return-value]


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _BoundMiddleware[**P, T]:
    call_next: Callable[P, Awaitable[T]]
    middleware: ClassicMiddleware[P, T]

    async def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return await self.middleware(self.call_next, *args, **kwargs)


def resolve_handler_source[**P, T](
    call_next: Callable[P, Awaitable[T]]
    | _BoundMiddleware[P, T]
    | HandleFunction[P, T],
    /,
) -> HandlerType[P, T] | Any:
    while True:
        try:
            call_next = call_next.call_next  # type: ignore[union-attr]
        except AttributeError:
            return call_next.source  # type: ignore[union-attr]


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _GeneratorMiddleware[**P, T]:
    middleware: GeneratorMiddleware[P, T]

    async def __call__(
        self,
        call_next: Callable[P, Awaitable[T]],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        generator: MiddlewareResult[T] = self.middleware(*args, **kwargs)
        value: T = NotImplemented

        try:
            await anext(generator)

            while True:
                try:
                    value = await call_next(*args, **kwargs)
                except BaseException as exc:
                    await generator.athrow(exc)
                else:
                    await generator.asend(value)
                    raise MiddlewareError(
                        f"Too many `yield` keywords in `{self.middleware}`."
                    )

        except StopAsyncIteration:
            ...

        finally:
            await generator.aclose()

        return value


def _is_gen_middleware[**P, T](
    middleware: Middleware[P, T],
) -> TypeGuard[GeneratorMiddleware[P, T]]:
    return any(map(isasyncgenfunction, (middleware, middleware.__call__)))  # type: ignore[operator]
