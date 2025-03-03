from abc import abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from functools import partial
from inspect import getmro, isclass
from typing import Any, Protocol, Self, runtime_checkable

import injection

type HandlerType[**P, T] = type[Handler[P, T]]
type HandlerFactory[**P, T] = Callable[..., Awaitable[Handler[P, T]]]


@runtime_checkable
class Handler[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    async def handle(self, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError


@runtime_checkable
class HandlerManager[I, O](Protocol):
    __slots__ = ()

    @abstractmethod
    def handlers_from(
        self,
        input_type: type[I],
    ) -> Iterator[Callable[[I], Awaitable[O]]]:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class MultipleHandlerManager[I, O](HandlerManager[I, O]):
    __factories: dict[type[I], list[HandlerFactory[[I], O]]] = field(
        default_factory=partial(defaultdict, list),
        init=False,
    )

    def handlers_from(
        self,
        input_type: type[I],
    ) -> Iterator[Callable[[I], Awaitable[O]]]:
        for it in getmro(input_type):
            for factory in self.__factories.get(it, ()):
                yield _make_handle_function(factory)

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        self.__factories[input_type].append(factory)
        return self


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SingleHandlerManager[I, O](HandlerManager[I, O]):
    __factories: dict[type[I], HandlerFactory[[I], O]] = field(
        default_factory=dict,
        init=False,
    )

    def handlers_from(
        self,
        input_type: type[I],
    ) -> Iterator[Callable[[I], Awaitable[O]]]:
        for it in getmro(input_type):
            factory = self.__factories.get(it, None)
            if factory is not None:
                yield _make_handle_function(factory)

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        if input_type in self.__factories:
            raise RuntimeError(
                f"A handler is already registered for the input type: `{input_type}`."
            )

        self.__factories[input_type] = factory
        return self


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class HandlerDecorator[I, O]:
    manager: HandlerManager[I, O]
    injection_module: injection.Module = field(default_factory=injection.mod)

    def __call__(self, input_type: type[I], /) -> Any:
        def decorator(wrapped: type[Handler[[I], O]]) -> type[Handler[[I], O]]:
            if not isclass(wrapped) or not issubclass(wrapped, Handler):
                raise TypeError(f"`{wrapped}` isn't a valid handler.")

            factory = self.injection_module.make_async_factory(wrapped)
            self.manager.subscribe(input_type, factory)
            return wrapped

        return decorator


def _make_handle_function[I, O](
    factory: HandlerFactory[[I], O],
) -> Callable[[I], Awaitable[O]]:
    return partial(__handle, factory=factory)


async def __handle[I, O](input_value: I, factory: HandlerFactory[[I], O]) -> O:
    handler = await factory()
    return await handler.handle(input_value)
