# Dispatching messages

To dispatch messages to their handlers, **python-cq** provides three bus classes: `CommandBus`, `QueryBus`, and `EventBus`.

Each bus can take a generic parameter to specify the return type of the `dispatch` method.

## Retrieving a bus

Bus instances are resolved through the configured DI adapter. When using the `[injection]` extra:

```python
from cq import CommandBus
from injection import inject

@inject
async def create_user(bus: CommandBus[None]):
    command = CreateUserCommand(name="John", email="john@example.com")
    await bus.dispatch(command)
```

## CommandBus

Use the CommandBus to dispatch commands. It returns the value produced by the handler.
```python
from cq import CommandBus

bus: CommandBus[None]
command = CreateUserCommand(name="John", email="john@example.com")
await bus.dispatch(command)
```

## QueryBus

Use the QueryBus to dispatch queries. It returns the value produced by the handler.
```python
from cq import QueryBus

bus: QueryBus[User]
query = GetUserByIdQuery(user_id)
user = await bus.dispatch(query)
```

## EventBus

Use the EventBus to dispatch events. Since events can be handled by multiple handlers (or none), it does not return a value.
```python
from cq import EventBus

bus: EventBus
event = UserCreatedEvent(user_id)
await bus.dispatch(event)
```
