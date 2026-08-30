# Dispatching messages

**python-cq** exposes three bus types to dispatch messages to their handlers: `CommandBus`, `QueryBus`, and `EventBus`. `CommandBus` and `QueryBus` take a generic parameter that types the value returned by `dispatch`. `EventBus` takes none, since it returns nothing.

A bus instance is obtained from your DI container. The examples below assume the bus has already been resolved; see [Configuring a bus](configuring.md) for how to build and register one.

## `CommandBus`

The `CommandBus` dispatches commands to their single registered handler and returns the handler's value:

```python
from cq import CommandBus

bus: CommandBus[int] = ...
command = CreateUserCommand(name="Ada", email="ada@example.com")
user_id = await bus.dispatch(command)
```

## `QueryBus`

The `QueryBus` dispatches queries to their single registered handler and returns the handler's value:

```python
from cq import QueryBus

bus: QueryBus[User] = ...
query = GetUserByIdQuery(user_id=42)
user = await bus.dispatch(query)
```

## `EventBus`

The `EventBus` fans an event out to every registered handler. It does not return a value, since multiple handlers may produce conflicting results.

```python
from cq import EventBus

bus: EventBus = ...
event = UserCreatedEvent(user_id=42)
await bus.dispatch(event)
```

Event handlers run concurrently inside a single `anyio` task group. `dispatch` returns once every handler has finished. If any handler raises (and is not declared with `fail_silently=True`), the exception is propagated through the task group, which may produce an `ExceptionGroup` when several handlers fail.

## When no handler is registered

If no handler matches the message type, `dispatch` returns the `NotImplemented` sentinel instead of raising. This is convenient when a message is optional in some contexts (for example a query that may or may not have a backing handler depending on configuration), but it means you should not assume a `dispatch` result is always meaningful:

```python
result = await bus.dispatch(SomeQuery())

if result is NotImplemented:
    # No handler is registered for SomeQuery.
    ...
```

The same sentinel is returned when a handler declared with `fail_silently=True` raises. For events, there is nothing to return, so the sentinel is not exposed.
