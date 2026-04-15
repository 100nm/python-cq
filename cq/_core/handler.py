from abc import abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from functools import partial
from inspect import Parameter, isclass, unwrap
from inspect import signature as inspect_signature
from typing import TYPE_CHECKING, Any, Protocol, Self, overload, runtime_checkable

from type_analyzer import MatchingTypesConfig, iter_matching_types, matching_types

from cq._core.common.typing import Decorator
from cq._core.di import DIAdapter, NoDI

type HandlerType[**P, T] = type[Handler[P, T]]
type HandlerFactory[**P, T] = Callable[..., Awaitable[Handler[P, T]]]


@runtime_checkable
class Handler[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    async def handle(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class HandleFunction[**P, T]:
    factory: HandlerFactory[P, T]
    source: HandlerType[P, T] | Any
    fail_silently: bool

    async def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        handler = await self.factory()
        return await handler.handle(*args, **kwargs)

    @classmethod
    def create(
        cls,
        factory: HandlerFactory[P, T],
        source: HandlerType[P, T] | None = None,
        fail_silently: bool = False,
    ) -> Self:
        return cls(factory, source or unwrap(factory), fail_silently)


@runtime_checkable
class HandlerRegistry[I, O](Protocol):
    __slots__ = ()

    @abstractmethod
    def handlers_from(self, input_type: type[I]) -> Iterator[HandleFunction[[I], O]]:
        raise NotImplementedError

    @abstractmethod
    def subscribe(
        self,
        input_type: type[I],
        handler_factory: HandlerFactory[[I], O],
        handler_type: HandlerType[[I], O] | None = ...,
        fail_silently: bool = ...,
    ) -> Self:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class MultipleHandlerRegistry[I, O](HandlerRegistry[I, O]):
    __values: dict[type[I], list[HandleFunction[[I], O]]] = field(
        default_factory=partial(defaultdict, list),
        init=False,
    )

    def handlers_from(self, input_type: type[I]) -> Iterator[HandleFunction[[I], O]]:
        for key_type in _iter_key_types(input_type):
            yield from self.__values.get(key_type, ())

    def subscribe(
        self,
        input_type: type[I],
        handler_factory: HandlerFactory[[I], O],
        handler_type: HandlerType[[I], O] | None = None,
        fail_silently: bool = False,
    ) -> Self:
        function = HandleFunction.create(handler_factory, handler_type, fail_silently)

        for key_type in _build_key_types(input_type):
            self.__values[key_type].append(function)

        return self


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SingleHandlerRegistry[I, O](HandlerRegistry[I, O]):
    __values: dict[type[I], HandleFunction[[I], O]] = field(
        default_factory=dict,
        init=False,
    )

    def handlers_from(self, input_type: type[I]) -> Iterator[HandleFunction[[I], O]]:
        for key_type in _iter_key_types(input_type):
            function = self.__values.get(key_type, None)
            if function is not None:
                yield function

    def subscribe(
        self,
        input_type: type[I],
        handler_factory: HandlerFactory[[I], O],
        handler_type: HandlerType[[I], O] | None = None,
        fail_silently: bool = False,
    ) -> Self:
        function = HandleFunction.create(handler_factory, handler_type, fail_silently)
        entries = {key_type: function for key_type in _build_key_types(input_type)}

        for key_type in entries:
            if key_type in self.__values:
                raise RuntimeError(
                    f"A handler is already registered for the input type: `{key_type}`."
                )

        self.__values.update(entries)
        return self


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class HandlerDecorator[I, O]:
    registry: HandlerRegistry[I, O]
    di: DIAdapter = field(default_factory=NoDI)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __call__(
            self,
            input_or_handler_type: type[I],
            /,
            *,
            fail_silently: bool = ...,
        ) -> Decorator: ...

        @overload
        def __call__[T](
            self,
            input_or_handler_type: T,
            /,
            *,
            fail_silently: bool = ...,
        ) -> T: ...

        @overload
        def __call__(
            self,
            input_or_handler_type: None = ...,
            /,
            *,
            fail_silently: bool = ...,
        ) -> Decorator: ...

    def __call__[T](
        self,
        input_or_handler_type: type[I] | T | None = None,
        /,
        *,
        fail_silently: bool = False,
    ) -> Any:
        if (
            input_or_handler_type is not None
            and isclass(input_or_handler_type)
            and issubclass(input_or_handler_type, Handler)
        ):
            return self.__decorator(
                input_or_handler_type,
                fail_silently=fail_silently,
            )

        return partial(
            self.__decorator,
            input_type=input_or_handler_type,  # type: ignore[arg-type]
            fail_silently=fail_silently,
        )

    def __decorator(
        self,
        wrapped: HandlerType[[I], O],
        /,
        *,
        input_type: type[I] | None = None,
        fail_silently: bool = False,
    ) -> HandlerType[[I], O]:
        factory = self.di.wire(wrapped)
        input_type = input_type or _resolve_input_type(wrapped)
        self.registry.subscribe(input_type, factory, wrapped, fail_silently)
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
