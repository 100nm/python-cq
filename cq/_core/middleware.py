from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Self

from cq.exceptions import MiddlewareError

type MiddlewareResult[T] = AsyncGenerator[None, T]
type Middleware[**P, T] = Callable[P, MiddlewareResult[T]]


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class MiddlewareGroup[**P, T]:
    __middlewares: list[Middleware[P, T]] = field(default_factory=list, init=False)

    def add(self, *middlewares: Middleware[P, T]) -> Self:
        self.__middlewares.extend(reversed(middlewares))
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
            handler = self.__apply_middleware(handler, middleware)

        return handler

    @classmethod
    def __apply_middleware(
        cls,
        handler: Callable[P, Awaitable[T]],
        middleware: Middleware[P, T],
    ) -> Callable[P, Awaitable[T]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            generator: MiddlewareResult[T] = middleware(*args, **kwargs)
            value: T = NotImplemented

            try:
                await anext(generator)

                while True:
                    try:
                        value = await handler(*args, **kwargs)
                    except BaseException as exc:
                        await generator.athrow(exc)
                    else:
                        await generator.asend(value)
                        raise MiddlewareError(
                            f"Too many `yield` keywords in `{middleware}`."
                        )

            except StopAsyncIteration:
                ...

            finally:
                await generator.aclose()

            return value

        return wrapper
