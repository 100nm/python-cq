from abc import abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterator, KeysView
from dataclasses import dataclass, field
from functools import partial
from inspect import Parameter, isclass, isfunction, unwrap
from inspect import signature as inspect_signature
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Protocol,
    Self,
    overload,
    runtime_checkable,
)

from type_analyzer import MatchingTypesConfig, iter_matching_types, matching_types

from cq._core.common.typing import Decorator
from cq._core.routing.di import DIAdapter, NoDI

type HandlerType[**P, T] = type[Handler[P, T]]
type HandlerFactory[**P, T] = Callable[..., Awaitable[Handler[P, T]]]


@runtime_checkable
class Handler[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    async def handle(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class HandlerEntry[**P, T]:
    function: Callable[P, Awaitable[T]]
    source: HandlerType[P, T] | Any
    fail_silently: bool

    async def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return await self.function(*args, **kwargs)

    @classmethod
    def from_factory(
        cls,
        factory: HandlerFactory[P, T],
        /,
        source: HandlerType[P, T] | None = None,
        fail_silently: bool = False,
    ) -> Self:
        function = partial(cls.__handle_with, factory)
        return cls(function, source or unwrap(factory), fail_silently)

    @classmethod
    def from_function(
        cls,
        function: Callable[P, Awaitable[T]],
        /,
        fail_silently: bool = False,
    ) -> Self:
        return cls(function, function, fail_silently)

    @staticmethod
    async def __handle_with(
        factory: HandlerFactory[P, T],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        handler = await factory()
        return await handler.handle(*args, **kwargs)


@runtime_checkable
class HandlerRegistry[I, O](Protocol):
    __slots__ = ()

    @property
    @abstractmethod
    def message_types(self) -> KeysView[type[I]]:
        raise NotImplementedError

    @abstractmethod
    def handlers_from(
        self,
        message_type: type[I],
    ) -> Iterator[HandlerEntry[Concatenate[I, ...], O]]:
        raise NotImplementedError

    @abstractmethod
    def subscribe(
        self,
        message_type: type[I],
        entry: HandlerEntry[Concatenate[I, ...], O],
    ) -> Self:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class MultipleHandlerRegistry[I, O](HandlerRegistry[I, O]):
    __values: dict[type[I], list[HandlerEntry[Concatenate[I, ...], O]]] = field(
        default_factory=partial(defaultdict, list),
        init=False,
    )

    @property
    def message_types(self) -> KeysView[type[I]]:
        return self.__values.keys()

    def handlers_from(
        self,
        message_type: type[I],
    ) -> Iterator[HandlerEntry[Concatenate[I, ...], O]]:
        for key_type in _iter_key_types(message_type):
            yield from self.__values.get(key_type, ())

    def subscribe(
        self,
        message_type: type[I],
        entry: HandlerEntry[Concatenate[I, ...], O],
    ) -> Self:
        for key_type in _build_key_types(message_type):
            self.__values[key_type].append(entry)

        return self


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SingleHandlerRegistry[I, O](HandlerRegistry[I, O]):
    __values: dict[type[I], HandlerEntry[Concatenate[I, ...], O]] = field(
        default_factory=dict,
        init=False,
    )

    @property
    def message_types(self) -> KeysView[type[I]]:
        return self.__values.keys()

    def handlers_from(
        self,
        message_type: type[I],
    ) -> Iterator[HandlerEntry[Concatenate[I, ...], O]]:
        for key_type in _iter_key_types(message_type):
            entry = self.__values.get(key_type, None)
            if entry is not None:
                yield entry

    def subscribe(
        self,
        message_type: type[I],
        entry: HandlerEntry[Concatenate[I, ...], O],
    ) -> Self:
        entries = {key_type: entry for key_type in _build_key_types(message_type)}

        for key_type in entries:
            if key_type in self.__values:
                raise RuntimeError(
                    f"A handler is already registered for the message type: `{key_type}`."
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
            message_type: type[I],
            /,
            *,
            fail_silently: bool = ...,
        ) -> Decorator: ...

        @overload
        def __call__[T](
            self,
            handler: T,
            /,
            *,
            fail_silently: bool = ...,
        ) -> T: ...

        @overload
        def __call__(
            self,
            nothing: None = ...,
            /,
            *,
            fail_silently: bool = ...,
        ) -> Decorator: ...

    def __call__[T](
        self,
        message_or_handler: type[I] | T | None = None,
        /,
        *,
        fail_silently: bool = False,
    ) -> Any:
        if self.__try_subscribe(message_or_handler, None, fail_silently):
            return message_or_handler

        return partial(
            self.__decorator,
            message_type=message_or_handler,  # type: ignore[arg-type]
            fail_silently=fail_silently,
        )

    def __decorator[T](
        self,
        wrapped: T,
        /,
        *,
        message_type: type[I] | None,
        fail_silently: bool,
    ) -> T:
        if not self.__try_subscribe(wrapped, message_type, fail_silently):
            raise TypeError(f"`{wrapped}` isn't a handler.")

        return wrapped

    def __try_subscribe(
        self,
        handler: Any,
        message_type: type[I] | None,
        fail_silently: bool,
    ) -> bool:
        if isfunction(handler):
            entry = HandlerEntry.from_function(handler, fail_silently)
            callee = handler

        elif isclass(handler) and issubclass(handler, Handler):
            factory = self.di.wire(handler)
            entry = HandlerEntry.from_factory(factory, handler, fail_silently)
            callee = handler.handle.__get__(NotImplemented, handler)

        else:
            return False

        message_type = message_type or _resolve_message_type(callee)
        self.registry.subscribe(message_type, entry)
        return True


def _build_key_types(message_type: Any) -> tuple[Any, ...]:
    config = MatchingTypesConfig(ignore_none=True)
    return matching_types(message_type, config)


def _iter_key_types(message_type: Any) -> Iterator[Any]:
    config = MatchingTypesConfig(
        with_bases=True,
        with_origin=True,
        with_type_alias_value=True,
    )
    return iter_matching_types(message_type, config)


def _resolve_message_type[I, O](
    handler: Callable[Concatenate[I, ...], Awaitable[O]],
) -> type[I]:
    signature = inspect_signature(handler, eval_str=True)

    for parameter in signature.parameters.values():
        message_type = parameter.annotation

        if message_type is Parameter.empty:
            break

        return message_type

    raise TypeError(
        f"Unable to resolve message type for handler `{handler}`, "
        "`handle` method must have a type annotation for its first parameter."
    )
