from dataclasses import dataclass, field
from typing import Any, ClassVar, Self

from cq._core.routing.dispatchers.abc import Dispatcher
from cq.exceptions import MissingTypeNameError

Command = object
Event = object
Query = object

type CommandBus[T] = Dispatcher[Command, T]
type EventBus = Dispatcher[Event, None]
type QueryBus[T] = Dispatcher[Query, T]

AnyCommandBus = CommandBus[Any]


@dataclass(frozen=True, slots=True)
class MessageTypeMetadata:
    type_name: str | None = field(default=None)
    correlation_id_field: str | None = field(default=None, kw_only=True)

    __field: ClassVar[str] = "__cq_metadata__"

    def __call__[T: type](self, wrapped: T, /) -> T:
        setattr(wrapped, self.__field, self)
        return wrapped

    def ensure_type_name(self) -> str:
        type_name = self.type_name
        if type_name is None:
            raise MissingTypeNameError(
                "The type has no name: decorate it with `@meta(...)`.",
            )

        return type_name

    def get_correlation_id[ID](self, message: object, /) -> ID | None:
        correlation_id_field = self.correlation_id_field
        if correlation_id_field is None:
            return getattr(message, "correlation_id", None)

        return getattr(message, correlation_id_field)

    def stringify_correlation_id(self, message: object, /) -> str | None:
        correlation_id = self.get_correlation_id(message)
        if correlation_id is None:
            return None

        return str(correlation_id)

    @classmethod
    def default(cls) -> Self:
        return cls()

    @classmethod
    def of(cls, something: Any, /) -> Self:
        return getattr(something, cls.__field, cls.default())
