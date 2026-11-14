# The router

`Router` is the object that connects everything in the routing part of the library. Handlers are registered on a router, buses are built by a router, and a router is what links both to your DI container.

## What a router holds

A router owns two things:

* **three handler registries**, one per message type. The command and query registries accept a single handler per message type, the event registry accepts any number;
* **a DI adapter**, used to instantiate handler classes, to open the command scope, and to register the buses in the container.

Everything else is derived from these two:

| Member                                             | Role                                                                           |
|----------------------------------------------------|--------------------------------------------------------------------------------|
| `command_handler`, `event_handler`, `query_handler` | Decorators that register a handler in the matching registry                    |
| `new_command_bus`, `new_event_bus`, `new_query_bus` | Factories that build a new bus reading from the matching registry              |
| `command_pipeline()`                               | Builds a `ContextCommandPipeline` that resolves the buses through the adapter  |
| `register_defaults()`                              | Registers the three bus factories in the DI container                         |
| `command_types`, `event_types`, `query_types`       | The message types that have at least one registered handler                   |
| `di`                                               | The DI adapter of the router                                                   |

A bus only knows the handlers of the router that built it. A handler registered with the decorator of one router is never reached by a bus built by another.

There are two ways to get a router:

* **the default router** of `cq.default`, ready to use, built on python-injection. Nothing to set up;
* **your own router**, built with the adapter you choose. Everything is explicit: you decide which container the handlers and buses live in, and nothing is registered by importing a module of the library.

## The default router

`cq.default` builds a router when it is imported, and exports its members as module-level names:

```python
from cq.default import command_handler, new_command_bus, router
```

`command_handler` is `router.command_handler`, `new_command_bus` is `router.new_command_bus`, and so on. This is why the guides import the decorators and bus factories from `cq.default`.

When it is built, the default router:

1. picks `cq.ext.injection.InjectionAdapter` as its DI adapter if the `[injection]` extra is installed, or a minimal adapter otherwise (see [Without an adapter](#without-an-adapter));
2. calls `register_defaults()`, so that `CommandBus`, `EventBus`, and `QueryBus` can be resolved from the container;
3. becomes the router used by `ContextCommandPipeline()` when no adapter is given.

None of this happens when importing `cq` alone. `cq` only exports types and building blocks, so the default router, and the buses it registers, only exist once `cq.default` has been imported.

## Creating your own router

Your own router gives you control over where things are registered. Its handlers and buses are isolated from the default router and from its container: they live in the adapter you pass, which can be an `InjectionAdapter` bound to a python-injection module of your own (see [python-injection](../integrations/injection.md#custom-module)) or an adapter for another container (see [Custom DI adapter](di.md)).

Build it with the adapter, call `register_defaults()` once, and use its members everywhere the guides use the ones of `cq.default`, which you then never import:

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

Pipelines follow the same rule. Build them from your router so they resolve the buses through your adapter, since `ContextCommandPipeline()` without argument relies on `cq.default`:

```python
class PaymentContext:
    pipeline: ClassVar[ContextCommandPipeline[ValidateCartCommand]] = (
        router.command_pipeline()
    )
```

## Without an adapter

`Router()` without argument uses a minimal adapter: handler classes are instantiated with no arguments, there is no command scope, and anything that needs to resolve a bus lazily (such as a pipeline) raises a `RuntimeError` as soon as it is created. This is also what the default router uses when the `[injection]` extra is not installed.
