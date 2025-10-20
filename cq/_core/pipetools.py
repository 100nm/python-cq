import injection

from cq._core.dispatcher.lazy import LazyDispatcher
from cq._core.dispatcher.pipe import ContextPipeline
from cq._core.message import AnyCommandBus, Command
from cq._core.scope import CQScope
from cq.middlewares.scope import InjectionScopeMiddleware


class ContextCommandPipeline[I: Command](ContextPipeline[I]):
    __slots__ = ()

    def __init__(
        self,
        /,
        *,
        injection_module: injection.Module | None = None,
        threadsafe: bool | None = None,
    ) -> None:
        dispatcher = LazyDispatcher(
            AnyCommandBus,
            injection_module=injection_module,
            threadsafe=threadsafe,
        )
        super().__init__(dispatcher)
        transaction_scope_middleware = InjectionScopeMiddleware(
            CQScope.TRANSACTION,
            exist_ok=True,
            threadsafe=threadsafe,
        )
        self.add_middlewares(transaction_scope_middleware)
