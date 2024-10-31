from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from typing import Self

from cq.exceptions import MiddlewareError

type MiddlewareResult[T] = AsyncGenerator[None, T]
type Middleware[**P, T] = Callable[P, MiddlewareResult[T]]


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class MiddlewareGroup[**P, T]:
    __middlewares: list[Middleware[P, T]] = field(default_factory=list, init=False)

    @property
    def __stack(self) -> Iterator[Middleware[P, T]]:
        return iter(self.__middlewares)

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
        return await self.__apply_stack(handler, self.__stack)(*args, **kwargs)

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

    @classmethod
    def __apply_stack(
        cls,
        handler: Callable[P, Awaitable[T]],
        stack: Iterator[Middleware[P, T]],
    ) -> Callable[P, Awaitable[T]]:
        for middleware in stack:
            new_handler = cls.__apply_middleware(handler, middleware)
            return cls.__apply_stack(new_handler, stack)

        return handler
