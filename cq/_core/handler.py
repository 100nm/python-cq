from abc import abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from functools import partial
from inspect import Parameter, isclass
from inspect import signature as inspect_signature
from typing import TYPE_CHECKING, Any, Protocol, Self, overload, runtime_checkable

import injection
from type_analyzer import MatchingTypesConfig, iter_matching_types, matching_types

type HandlerType[**P, T] = type[Handler[P, T]]
type HandlerFactory[**P, T] = Callable[..., Awaitable[Handler[P, T]]]


@runtime_checkable
class Handler[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    async def handle(self, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError


@runtime_checkable
class HandlerRegistry[I, O](Protocol):
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
class MultipleHandlerRegistry[I, O](HandlerRegistry[I, O]):
    __factories: dict[type[I], list[HandlerFactory[[I], O]]] = field(
        default_factory=partial(defaultdict, list),
        init=False,
    )

    def handlers_from(
        self,
        input_type: type[I],
    ) -> Iterator[Callable[[I], Awaitable[O]]]:
        for key_type in _iter_key_types(input_type):
            for factory in self.__factories.get(key_type, ()):
                yield _make_handle_function(factory)

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        for key_type in _build_key_types(input_type):
            self.__factories[key_type].append(factory)

        return self


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SingleHandlerRegistry[I, O](HandlerRegistry[I, O]):
    __factories: dict[type[I], HandlerFactory[[I], O]] = field(
        default_factory=dict,
        init=False,
    )

    def handlers_from(
        self,
        input_type: type[I],
    ) -> Iterator[Callable[[I], Awaitable[O]]]:
        for key_type in _iter_key_types(input_type):
            factory = self.__factories.get(key_type, None)
            if factory is not None:
                yield _make_handle_function(factory)

    def subscribe(self, input_type: type[I], factory: HandlerFactory[[I], O]) -> Self:
        entries = {key_type: factory for key_type in _build_key_types(input_type)}

        for key_type in entries:
            if key_type in self.__factories:
                raise RuntimeError(
                    f"A handler is already registered for the input type: `{key_type}`."
                )

        self.__factories.update(entries)
        return self


class _Decorator(Protocol):
    def __call__[T](self, wrapped: T, /) -> T: ...


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class HandlerDecorator[I, O]:
    registry: HandlerRegistry[I, O]
    injection_module: injection.Module = field(default_factory=injection.mod)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __call__(
            self,
            input_or_handler_type: type[I],
            /,
            *,
            threadsafe: bool | None = ...,
        ) -> _Decorator: ...

        @overload
        def __call__[T](
            self,
            input_or_handler_type: T,
            /,
            *,
            threadsafe: bool | None = ...,
        ) -> T: ...

        @overload
        def __call__(
            self,
            input_or_handler_type: None = ...,
            /,
            *,
            threadsafe: bool | None = ...,
        ) -> _Decorator: ...

    def __call__[T](
        self,
        input_or_handler_type: type[I] | T | None = None,
        /,
        *,
        threadsafe: bool | None = None,
    ) -> Any:
        if (
            input_or_handler_type is not None
            and isclass(input_or_handler_type)
            and issubclass(input_or_handler_type, Handler)
        ):
            return self.__decorator(input_or_handler_type, threadsafe=threadsafe)

        return partial(
            self.__decorator,
            input_type=input_or_handler_type,  # type: ignore[arg-type]
            threadsafe=threadsafe,
        )

    def __decorator(
        self,
        wrapped: HandlerType[[I], O],
        /,
        *,
        input_type: type[I] | None = None,
        threadsafe: bool | None = None,
    ) -> HandlerType[[I], O]:
        factory = self.injection_module.make_async_factory(wrapped, threadsafe)
        input_type = input_type or _resolve_input_type(wrapped)
        self.registry.subscribe(input_type, factory)
        return wrapped


def _build_key_types(input_type: Any) -> tuple[Any, ...]:
    config = MatchingTypesConfig(ignore_none=True)
    return matching_types(input_type, config)


def _iter_key_types(input_type: Any) -> Iterator[Any]:
    config = MatchingTypesConfig(
        with_bases=True,
        with_origin=True,
        with_type_alias_value=True,
    )
    return iter_matching_types(input_type, config)


def _resolve_input_type[I, O](handler_type: HandlerType[[I], O]) -> type[I]:
    fake_method = handler_type.handle.__get__(NotImplemented, handler_type)
    signature = inspect_signature(fake_method, eval_str=True)

    for parameter in signature.parameters.values():
        input_type = parameter.annotation

        if input_type is Parameter.empty:
            break

        return input_type

    raise TypeError(
        f"Unable to resolve input type for handler `{handler_type}`, "
        "`handle` method must have a type annotation for its first parameter."
    )


def _make_handle_function[I, O](
    factory: HandlerFactory[[I], O],
) -> Callable[[I], Awaitable[O]]:
    return partial(__handle, factory=factory)


async def __handle[I, O](input_value: I, *, factory: HandlerFactory[[I], O]) -> O:
    handler = await factory()
    return await handler.handle(input_value)
