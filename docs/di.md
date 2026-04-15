# Custom DI

**python-cq** abstracts dependency injection behind the `DIAdapter` protocol, allowing you to integrate any DI framework.

## The `CQ` class

`CQ` is the central object that binds together the handler registries and the DI adapter. The module-level decorators (`command_handler`, `event_handler`, `query_handler`) and bus factories (`new_command_bus`, `new_event_bus`, `new_query_bus`) all derive from a default `CQ` instance created at import time.

You can create additional isolated instances when you need separate handler registries, for example in tests or in a multi-tenant setup:

```python
from cq import CQ, ContextCommandPipeline

cq = CQ(my_di_adapter).register_defaults()

command_handler = cq.command_handler
event_handler = cq.event_handler
query_handler = cq.query_handler

new_command_bus = cq.new_command_bus
new_event_bus = cq.new_event_bus
new_query_bus = cq.new_query_bus
```

When using `ContextCommandPipeline`, pass `cq.di` explicitly so it uses the same DI adapter:

```python
ContextCommandPipeline(cq.di)
```

## Implementing a `DIAdapter`

`DIAdapter` is a `Protocol`. Implement it to integrate any DI framework:

```python
from collections.abc import Awaitable, Callable
from cq import CQ, DIAdapter, CommandBus, EventBus, QueryBus
from typing import Any, AsyncContextManager

class MyDIAdapter(DIAdapter):
    def command_scope(self) -> AsyncContextManager[None]:
        # Return an async context manager that:
        # - opens a DI scope for the duration of a command dispatch
        # - manages the lifecycle of a RelatedEvents instance within that scope
        # - silently ignores nested activations (re-entrant calls)
        ...

    def lazy[T](self, tp: type[T]) -> Callable[[], Awaitable[T]]:
        # Ask the DI framework for a resolver for `tp`.
        # The returned callable, when called and awaited, performs the resolution.
        ...

    def register_defaults(
        self,
        command_bus: Callable[..., CommandBus[Any]],
        event_bus: Callable[..., EventBus],
        query_bus: Callable[..., QueryBus[Any]],
    ) -> None:
        # Register the bus factories as default providers so that handlers
        # can declare CommandBus, EventBus, or QueryBus as dependencies.
        # This method is optional; the default implementation is a no-op.
        ...

    def wire[T](self, tp: type[T]) -> Callable[..., Awaitable[T]]:
        # Return an async factory that instantiates `tp` with injected dependencies.
        # Used internally to build handler instances.
        ...


cq = CQ(MyDIAdapter()).register_defaults()
```
