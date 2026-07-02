# Custom DI adapter

!!! note
    If you installed `python-cq[injection]`, you can skip this page. The default DI integration with [python-injection](https://github.com/100nm/python-injection) is already wired up. This guide is only useful if you want to plug in a different DI framework (or none at all).

**python-cq** does not depend on any specific dependency injection container. Instead, it talks to DI through the `DIAdapter` protocol. Implement this protocol once and you can use the library with any container you already have in your project.

## The `CQ` class

`CQ` ties together the handler registries and the DI adapter. The module-level decorators (`command_handler`, `event_handler`, `query_handler`) and bus factories (`new_command_bus`, `new_event_bus`, `new_query_bus`) all derive from a default `CQ` instance built at import time.

You create your own `CQ` instance to wire the library against a custom `DIAdapter`:

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

When you build a `ContextCommandPipeline` against a non-default `CQ`, pass its DI adapter explicitly so the pipeline dispatches through the right buses:

```python
ContextCommandPipeline(cq.di)
```

If you use the default `CQ`, `ContextCommandPipeline()` (with no argument) is enough.

## Implementing a `DIAdapter`

`DIAdapter` is a `Protocol` with four methods, three of them required:

```python
from collections.abc import Awaitable, Callable
from cq import CQ, Command, DIAdapter, CommandBus, EventBus, Middleware, QueryBus
from typing import Any

class MyDIAdapter(DIAdapter):
    def command_scope(self) -> Middleware[[Command], Any]:
        """
        Return a middleware that wraps each command dispatch.

        Responsibilities:
          1. Open a DI scope for the duration of the command.
          2. Build a `RelatedEvents` instance inside that scope and make it
             resolvable, so command handlers can inject it.

        If you already have an async context manager for the scope, wrap it
        with `cq.middlewares.contextlib.AsyncContextManagerMiddleware` instead
        of writing the middleware by hand.
        """
        ...

    def lazy[T](self, tp: type[T]) -> Callable[[], Awaitable[T]]:
        """
        Return a callable that, when called and awaited, resolves `tp` from
        the container. Used to wire up bus references lazily so that buses
        configured later in the import graph are still picked up.
        """
        ...

    def register_defaults(
        self,
        command_bus: Callable[..., CommandBus[Any]],
        event_bus: Callable[..., EventBus],
        query_bus: Callable[..., QueryBus[Any]],
    ) -> None:
        """
        Register the bus factories with the container so that handlers can
        declare `CommandBus`, `EventBus`, or `QueryBus` as dependencies.

        Optional: the default implementation is a no-op, which is fine if
        your container does not need explicit registration.
        """
        ...

    def wire[T](self, tp: type[T]) -> Callable[..., Awaitable[T]]:
        """
        Return an async factory that instantiates `tp` with injected
        dependencies. Used internally to build handler instances.
        """
        ...

cq = CQ(MyDIAdapter()).register_defaults()
```

The reference implementation for python-injection lives in `cq.ext.injection.InjectionAdapter`. It is a good starting point if you need to model your own adapter on a working example.
