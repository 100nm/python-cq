# Custom DI adapter

!!! note
    If you installed `python-cq[injection]`, you can skip this page. The integration with [python-injection](https://github.com/100nm/python-injection) is already wired up (see [python-injection](../integrations/injection.md)). This page is only useful to plug in a different DI framework.

**python-cq** does not depend on a specific dependency injection container. It talks to DI through the `DIAdapter` protocol: implement it once and the library works with the container you already use.

## The `Router` class

`Router` ties the handler registries to a DI adapter. The decorators (`command_handler`, `event_handler`, `query_handler`) and bus factories (`new_command_bus`, `new_event_bus`, `new_query_bus`) exported by `cq` are bound to a default `Router` built at import time, which uses python-injection when the extra is installed.

To use your own adapter, create a `Router` with it and use its methods in place of the module-level ones:

```python
from cq import Router

router = Router(MyDIAdapter()).register_defaults()

command_handler = router.command_handler
event_handler = router.event_handler
query_handler = router.query_handler

new_command_bus = router.new_command_bus
new_event_bus = router.new_event_bus
new_query_bus = router.new_query_bus
```

`register_defaults()` hands the bus factories to the adapter so that `CommandBus`, `EventBus`, and `QueryBus` can be resolved from the container. Call it once per router.

A router also lists the message types its handlers are registered for, through `command_types`, `event_types`, and `query_types`.

Pipelines follow the same rule. Build them from your router so they resolve the buses through your adapter:

```python
class PaymentContext:
    pipeline: ClassVar[ContextCommandPipeline[ValidateCartCommand]] = (
        router.command_pipeline()
    )
```

## Implementing a `DIAdapter`

`DIAdapter` is a `Protocol` with four methods. `lazy` and `wire` are required, `command_scope` and `register_defaults` are optional:

```python
from collections.abc import Awaitable, Callable
from cq import Command, CommandBus, DIAdapter, EventBus, Middleware, QueryBus, Router
from typing import Any, Concatenate


class MyDIAdapter(DIAdapter):
    def command_scope(self) -> Middleware[Concatenate[Command, ...], Any] | None:
        """
        Return a middleware that wraps each command dispatch.

        It must create a `RelatedEvents` instance, make it resolvable for as
        long as the dispatch lasts so that command handlers can inject it,
        and wait for the scheduled events before the dispatch returns.

        Optional: by default no middleware wraps the dispatch, and command
        handlers have no `RelatedEvents` to inject.
        """
        ...

    def lazy[T](self, tp: type[T]) -> Callable[[], Awaitable[T]]:
        """
        Return a callable that, when called and awaited, resolves `tp` from
        the container. Pipelines call the returned callable on every
        message they dispatch, so that buses registered later in the import
        graph are picked up.
        """
        ...

    def register_defaults(
        self,
        command_bus: Callable[..., CommandBus[Any]],
        event_bus: Callable[..., EventBus],
        query_bus: Callable[..., QueryBus[Any]],
    ) -> None:
        """
        Register the bus factories with the container so that `CommandBus`,
        `EventBus`, and `QueryBus` can be declared as dependencies.

        Optional: the default implementation does nothing.
        """
        ...

    def wire[T](self, tp: type[T]) -> Callable[..., Awaitable[T]]:
        """
        Return an async factory that instantiates `tp` with its dependencies
        injected. Called once per handler at registration, and the factory
        is awaited on every dispatch.
        """
        ...


router = Router(MyDIAdapter()).register_defaults()
```

### The command scope

`AnyIORelatedEvents` is the ready-made `RelatedEvents` implementation. It is an async context manager that takes the function used to emit each event, usually an `EventBus`, and waits for every scheduled event on exit. A command scope typically opens one per dispatch and exposes it to the container:

```python
from cq import AnyIORelatedEvents, EventBus, MiddlewareResult, RelatedEvents
from dataclasses import dataclass
from typing import Any


@dataclass
class CommandScopeMiddleware:
    event_bus: EventBus

    async def __call__(self, command) -> MiddlewareResult[Any]:
        async with AnyIORelatedEvents(self.event_bus) as events:
            with container.override(RelatedEvents, events):
                yield
```

Your adapter's `command_scope` returns an instance of this class, built with the event bus. `container.override` stands for whatever your container provides. If your container already exposes the scope as an async context manager, wrap it with `cq.middlewares.contextlib.AsyncContextManagerMiddleware` instead of writing the middleware by hand.

You can also write your own `RelatedEvents` (an outbox, an implementation that enriches events with a correlation id, ...). The protocol only requires an `add(*events)` method.

### Passing `RelatedEvents` as an argument

If your container cannot scope a dependency to a dispatch, there is a workaround: the command scope can pass `RelatedEvents` to the handler as an extra argument of `call_next`, which is forwarded down to `handle`. Prefer a scoped dependency whenever your container supports one.

!!! warning
    This changes the signature of every command handler, not only those that publish events: each `handle` must accept the extra parameter, otherwise its dispatch raises a `TypeError`.

```python
from cq import AnyIORelatedEvents, EventBus
from dataclasses import dataclass


@dataclass
class CommandScopeMiddleware:
    event_bus: EventBus

    async def __call__(self, call_next, command):
        async with AnyIORelatedEvents(self.event_bus) as events:
            return await call_next(command, events)
```

Command handlers then receive the events as the second parameter of `handle`, instead of as a constructor dependency:

```python
from cq import RelatedEvents, command_handler
from typing import NamedTuple


@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository

    async def handle(self, command: CreateUserCommand, events: RelatedEvents) -> int:
        user = await self.repository.create(command.name, command.email)
        events.add(UserCreatedEvent(user_id=user.id))
        return user.id
```

The middlewares you add to the bus are not affected: they sit outside the command scope (see [Execution order](middlewares.md#execution-order)) and only receive the command.

## Without an adapter

`Router()` without argument uses a minimal adapter: handlers are instantiated with no arguments, there is no command scope, and anything that needs to resolve a bus lazily (such as a pipeline) raises a `RuntimeError` as soon as it is created. This is also what the default router uses when the `[injection]` extra is not installed.

The reference implementation for python-injection lives in `cq.ext.injection.InjectionAdapter`. It is a good starting point to model your own adapter on a working example.
