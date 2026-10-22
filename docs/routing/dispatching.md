# Dispatching messages

**python-cq** exposes three bus types: `CommandBus`, `QueryBus`, and `EventBus`. `CommandBus` and `QueryBus` take a type parameter for the value returned by `dispatch`. `EventBus` takes none, since it returns nothing.

A bus is obtained from your DI container. With the `[injection]` extra, the three types are registered by default, so you can declare them as dependencies right away:

```python
from cq import CommandBus
from injection import inject


@inject
async def create_user(bus: CommandBus[int]) -> int:
    return await bus.dispatch(CreateUserCommand(name="Ada", email="ada@example.com"))
```

To customize a bus with listeners or middlewares, see [Configuring a bus](configuring.md).

## `CommandBus`

The `CommandBus` sends a command to its single handler and returns the handler's value:

```python
from cq import CommandBus

bus: CommandBus[int] = ...
user_id = await bus.dispatch(CreateUserCommand(name="Ada", email="ada@example.com"))
```

Each dispatch runs inside a command scope opened by the DI adapter. This is what makes `RelatedEvents` injectable in command handlers.

`AnyCommandBus` is a shorthand for `CommandBus[Any]`, handy when one bus dispatches commands with different return types.

## `QueryBus`

The `QueryBus` sends a query to its single handler and returns the handler's value:

```python
from cq import QueryBus

bus: QueryBus[User] = ...
user = await bus.dispatch(GetUserByIdQuery(user_id=42))
```

## `EventBus`

The `EventBus` fans an event out to every registered handler. It does not return a value, since several handlers may produce conflicting results.

```python
from cq import EventBus

bus: EventBus = ...
await bus.dispatch(UserCreatedEvent(user_id=42))
```

Event handlers run concurrently inside a single `anyio` task group. `dispatch` returns once every handler has finished. If a handler raises (and is not declared with `fail_silently=True`), the remaining handlers are cancelled and the exception comes out of `dispatch` inside an `ExceptionGroup`.

## Buses are callables

Every bus is also an async callable: `await bus(message)` is the same as `await bus.dispatch(message)`. This lets you pass a bus anywhere an `async (message) -> result` function is expected, for example as the dispatcher of a [`Pump`](../queuing/pump.md).

## When no handler is registered

If no handler matches the message type, `dispatch` returns the `NotImplemented` sentinel instead of raising. This is convenient when a message is optional in some contexts (a query that may or may not have a backing handler depending on configuration), but it means a `dispatch` result is not always meaningful:

```python
result = await bus.dispatch(SomeQuery())

if result is NotImplemented:
    # No handler is registered for SomeQuery.
    ...
```

The same sentinel is returned when a handler declared with `fail_silently=True` raises. For events, there is nothing to return, so the sentinel is not exposed.
