# python-injection

[python-injection](https://github.com/100nm/python-injection) is the default DI backend of **python-cq**. Install it with the `[injection]` extra:

```bash
pip install "python-cq[injection]"
```

With the extra installed, the default router uses `cq.ext.injection.InjectionAdapter`, so there is nothing to wire. This page describes what the adapter sets up, and how to tune it.

## What is wired

* **Handlers** are built through the container on every dispatch: each constructor parameter is resolved from its type annotation.
* **Buses**: `CommandBus`, `EventBus`, and `QueryBus` are registered as fallbacks, so they can be injected right away, and any factory you register for them takes precedence (see [Configuring a bus](../routing/configuring.md)).
* **Command scope**: each command dispatch opens a python-injection scope named `CQScope.COMMAND_DISPATCH`. `RelatedEvents` is registered in this scope, which is what makes it injectable in command handlers.
* **Pipelines** resolve the buses from the container each time they dispatch a message.

Everything is registered in the default python-injection module, the one used by the `@injectable`, `@inject`, and `@scoped` decorators imported from `injection`.

## Dependencies scoped to a command

The command scope is a regular python-injection scope, so your own dependencies can live in it too. A dependency declared with `@scoped(CQScope.COMMAND_DISPATCH)` is created once per command dispatch, and shared by everything resolved during that dispatch. A typical use is a transaction shared by several repositories:

```python
from collections.abc import AsyncIterator
from cq.ext.injection import CQScope
from injection import scoped


@scoped(CQScope.COMMAND_DISPATCH)
async def transaction_factory(database: Database) -> AsyncIterator[Transaction]:
    async with database.transaction() as transaction:
        yield transaction
```

Every repository that depends on `Transaction` receives the same one during a command dispatch, so everything the command writes is committed together when its dispatch ends, or rolled back if it raises. The next command gets a new transaction. `Database` and `Transaction` stand for whatever your storage library provides.

Resolving a dependency of the command scope outside a command dispatch raises a python-injection `ScopeUndefinedError`.

!!! warning
    The command scope belongs to the command handler only. An event handler must not depend on anything scoped to `CQScope.COMMAND_DISPATCH`, even for an event published through `RelatedEvents`. Where and when related events are handled is a configuration choice: they may be [sent to a queue](#sending-related-events-to-a-queue) and handled after the command, or in another process. Even when they are dispatched in-process, they can run while the scope is closing, and resolving the dependency then raises a python-injection `ScopeError`. Put what an event handler needs in the event itself, or give it its own dependencies.

## Sending related events to a queue

By default, related events are dispatched on the `EventBus` before the command dispatch returns. To handle them later instead, register your own `RelatedEvents` in the command scope. It takes precedence over the default one:

```python
from collections.abc import AsyncIterator
from cq import AnyIORelatedEvents, RelatedEvents
from cq.ext.injection import CQScope
from injection import scoped


@scoped(CQScope.COMMAND_DISPATCH)
async def related_events_factory(
    queue: EventQueue,
) -> AsyncIterator[RelatedEvents]:
    async with AnyIORelatedEvents(queue) as events:
        yield events
```

`AnyIORelatedEvents` takes the function that emits each event. A queue's producer is callable, so it fits here. The command dispatch now only waits for the events to be sent, and a [`Pump`](../queuing/pump.md) drains the queue into the `EventBus`. `EventQueue` stands for the queue registered in your container, for example a [`MemoryQueue`](../queuing/queues.md#memoryqueue) subclass or your own transport.

## Custom module

To register everything in another python-injection module than the default one, build a `Router` with your own `InjectionAdapter`, as described in [Custom DI adapter](../routing/di.md#the-router-class):

```python
from cq import Router
from cq.ext.injection import InjectionAdapter
from enum import StrEnum
from injection import mod


class Profile(StrEnum):
    APP = "app"


router = Router(InjectionAdapter(mod(Profile.APP))).register_defaults()
```

`InjectionAdapter` accepts two parameters:

* `module`: the python-injection module where handlers are resolved and buses are registered. Defaults to the default module.
* `threadsafe`: forwarded to python-injection whenever the adapter resolves a dependency or opens the command scope. With `True`, the resolution is wrapped in a lock. Defaults to `None`, which leaves the choice to python-injection.

## Opening a scope around other dispatches

`cq.ext.injection.InjectionScopeMiddleware` is the middleware behind the command scope. Add it to any bus, pipeline, or pump to open a python-injection scope around each message:

```python
from cq import Pump
from cq.ext.injection import InjectionScopeMiddleware
from enum import StrEnum


class DIScope(StrEnum):
    MESSAGE = "message"


pump = Pump(queue, event_bus).add_middlewares(InjectionScopeMiddleware(DIScope.MESSAGE))
```

Opening a scope that is already open raises a python-injection `ScopeAlreadyDefinedError`. Pass `exist_ok=True` to reuse the open scope instead, for example when the same middleware can be nested in another dispatch:

```python
InjectionScopeMiddleware(DIScope.MESSAGE, exist_ok=True)
```

It also accepts `threadsafe`, with the same meaning as on `InjectionAdapter`.
