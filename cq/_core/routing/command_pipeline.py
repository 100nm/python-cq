from typing import TYPE_CHECKING, Any, ClassVar, Self, overload

from cq._core.common.typing import Decorator
from cq._core.message import Command, CommandBus, Query, QueryBus
from cq._core.routing.di import DIAdapter
from cq._core.routing.dispatchers.abc import Dispatcher
from cq._core.routing.dispatchers.lazy import LazyDispatcher
from cq._core.routing.dispatchers.pipe import (
    ContextPipeline,
    ConvertMethod,
    ConvertMethodAsync,
    ConvertMethodSync,
)


class ContextCommandPipeline[C: Command](ContextPipeline[C]):
    __slots__ = ("__query_dispatcher",)

    __query_dispatcher: Dispatcher[Query, Any]

    __default_di: ClassVar[DIAdapter]

    def __init__(self, di: DIAdapter | None = None, /) -> None:
        di = di or self.__default_di
        super().__init__(LazyDispatcher(CommandBus, di))
        self.__query_dispatcher = LazyDispatcher(QueryBus, di)

    def add_static_query_step[Q: Query](self, query: Q, /) -> Self:
        return self.add_static_step(query, dispatcher=self.__query_dispatcher)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def query_step[Q: Query](
            self,
            wrapped: ConvertMethodAsync[Q, Any],
            /,
        ) -> ConvertMethodAsync[Q, Any]: ...

        @overload
        def query_step[Q: Query](
            self,
            wrapped: ConvertMethodSync[Q, Any],
            /,
        ) -> ConvertMethodSync[Q, Any]: ...

        @overload
        def query_step(self, wrapped: None = ..., /) -> Decorator: ...

    def query_step[Q: Query](  # type: ignore[misc]
        self,
        wrapped: ConvertMethod[Q, Any] | None = None,
        /,
    ) -> Any:
        return self.step(wrapped, dispatcher=self.__query_dispatcher)

    @classmethod
    def _set_default_di(cls, di: DIAdapter, /) -> None:
        cls.__default_di = di
