from typing import TYPE_CHECKING, Any, Callable, overload

import injection

from cq import Dispatcher
from cq._core.dispatcher.lazy import LazyDispatcher
from cq._core.dispatcher.pipe import ContextPipeline, PipeConverterMethod
from cq._core.message import AnyCommandBus, Command, Query, QueryBus
from cq._core.scope import CQScope
from cq.middlewares.scope import InjectionScopeMiddleware


class ContextCommandPipeline[I: Command](ContextPipeline[I]):
    __slots__ = ("__query_dispatcher",)

    __query_dispatcher: Dispatcher[Query, Any]

    def __init__(
        self,
        /,
        *,
        injection_module: injection.Module | None = None,
        threadsafe: bool | None = None,
    ) -> None:
        command_dispatcher = LazyDispatcher(
            AnyCommandBus,
            injection_module=injection_module,
            threadsafe=threadsafe,
        )
        super().__init__(command_dispatcher)

        self.__query_dispatcher = LazyDispatcher(
            QueryBus,
            injection_module=injection_module,
            threadsafe=threadsafe,
        )

        transaction_scope_middleware = InjectionScopeMiddleware(
            CQScope.TRANSACTION,
            exist_ok=True,
            threadsafe=threadsafe,
        )
        self.add_middlewares(transaction_scope_middleware)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def query_step[T: Query](
            self,
            wrapped: PipeConverterMethod[T, Any],
            /,
        ) -> PipeConverterMethod[T, Any]: ...

        @overload
        def query_step[T: Query](
            self,
            wrapped: None = ...,
            /,
        ) -> Callable[[PipeConverterMethod[T, Any]], PipeConverterMethod[T, Any]]: ...

    def query_step[T: Query](
        self,
        wrapped: PipeConverterMethod[T, Any] | None = None,
        /,
    ) -> Any:
        return self.step(wrapped, dispatcher=self.__query_dispatcher)
