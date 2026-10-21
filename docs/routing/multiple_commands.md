# Executing multiple commands

In CQRS, the saga pattern is the usual way to orchestrate a sequence of commands. Sagas are designed for distributed systems and can feel overengineered for a local workflow. **python-cq** offers two lightweight alternatives for running several commands in-process:

* `dispatch_sequentially` when the messages are known up front and do not depend on each other's results;
* `ContextCommandPipeline` when each command is built from the result of the previous one.

## `dispatch_sequentially`

`dispatch_sequentially` takes a dispatcher and any number of messages. It dispatches them in the given order, waiting for each one to complete before starting the next, and returns the results as a tuple in the same order.

A typical use is to drive the system into a known state through its own commands, for example when setting up a test:

```python
from cq import AnyCommandBus, dispatch_sequentially

bus: AnyCommandBus = ...
account_id = 42

_, _, subscription = await dispatch_sequentially(
    bus,
    CreateAccountCommand(account_id=account_id, email="ada@example.com"),
    SubscribeToPlanCommand(account_id=account_id, plan="pro"),
    SuspendSubscriptionCommand(account_id=account_id, reason="payment_failed"),
)
```

Each command goes through the real handlers and middlewares, so the resulting state is exactly what the application would produce. The dispatcher can be any `Dispatcher`: a `CommandBus`, a `QueryBus`, or an `EventBus`. If a handler raises, the exception propagates immediately and the remaining messages are not dispatched.

The result tuple is typed with a variadic type parameter that cannot be inferred from the arguments, so annotate the target to get precise element types:

```python
results: tuple[Account, Subscription, Subscription] = await dispatch_sequentially(
    bus,
    create_account,
    subscribe,
    suspend,
)
```

Each message is dispatched exactly as `bus.dispatch` would, so the [`NotImplemented` sentinel](dispatching.md#when-no-handler-is-registered) can appear in the tuple when a message has no handler.

## `ContextCommandPipeline`

A pipeline runs a sequence of commands. Each step receives the result of the previous command and produces the next command to dispatch. The class that holds the pipeline is the context: instance attributes assigned in one step are visible in the next.

```python
from cq import ContextCommandPipeline


class PaymentContext:
    transaction_id: int

    pipeline: ContextCommandPipeline[ValidateCartCommand] = ContextCommandPipeline()

    @pipeline.step
    def _(self, result: CartValidatedResult) -> CreateTransactionCommand:
        return CreateTransactionCommand(cart_id=result.cart_id, amount=result.total)

    @pipeline.step
    def _(self, result: TransactionCreatedResult) -> NotifyMerchantCommand:
        self.transaction_id = result.transaction_id
        return NotifyMerchantCommand(transaction_id=result.transaction_id)

    @pipeline.step
    def _(self, result: MerchantNotifiedResult): ...
```

The pipeline resolves `CommandBus` and `QueryBus` from the DI container the first time it dispatches, so the buses you configure in your container are the ones it uses. If you manage your own `Router` (see [Custom DI adapter](di.md)), build the pipeline with `router.command_pipeline()` instead.

### Steps

A step is a method decorated with `@pipeline.step`. It receives the value returned by the previous command's handler and returns the next command to dispatch. Steps can be sync or async.

A step that returns `None` stops the pipeline. This is the natural way to write a terminal step that only consumes the previous result, and it also lets earlier steps abort the pipeline conditionally:

```python
@pipeline.step
def _(self, result: ValidationResult):
    if result.is_valid:
        return PersistCommand(...)

    return None  # stop here, skip the rest of the pipeline
```

### Query steps

`@pipeline.query_step` works like `@pipeline.step`, but the message it produces is dispatched through the `QueryBus`:

```python
@pipeline.query_step
def _(self, result: TransactionCreatedResult) -> GetMerchantByIdQuery:
    return GetMerchantByIdQuery(merchant_id=result.merchant_id)
```

### Static steps

When a step does not depend on the previous result, declare it with `add_static_step` (for a command) or `add_static_query_step` (for a query). The given message is dispatched as is each time the pipeline runs:

```python
class WarmCacheContext:
    pipeline: ContextCommandPipeline[StartCommand] = ContextCommandPipeline()

    pipeline.add_static_step(LoadConfigCommand())
    pipeline.add_static_query_step(GetActiveUsersQuery())

    @pipeline.step
    def _(self, users: list[User]) -> WarmCacheCommand:
        return WarmCacheCommand(user_ids=[user.id for user in users])
```

Static and decorated steps run in the order they are declared in the class body.

### Running a pipeline

Calling `Context.pipeline(initial_command)` builds a fresh `Context` instance, runs every step against it, and returns the populated context:

```python
async def process_payment(cart_id: int) -> int:
    context = await PaymentContext.pipeline(ValidateCartCommand(cart_id=cart_id))
    return context.transaction_id
```

Each run gets its own context instance, so attributes set in one run do not leak into the next. The context class is instantiated without arguments in this form.

### Seeding the context

If a step needs values that are known before the first command runs, instantiate the context yourself and call `pipeline` on the instance. The same object is returned at the end, mutated by every step that ran.

Because the input and the returned context are the same object, the recommended pattern is to hide both behind a `run` classmethod:

```python
from cq import ContextCommandPipeline
from typing import ClassVar, Self
from uuid import UUID


class LinkOAuthAccountContext:
    pipeline: ClassVar[ContextCommandPipeline[VerifyIDTokenCommand]] = (
        ContextCommandPipeline()
    )

    def __init__(self, user_id: UUID, provider: OAuthProvider) -> None:
        self.user_id = user_id
        self.provider = provider

    @pipeline.step
    def _(self, user: OAuthUser) -> LinkOAuthAccountCommand:
        return LinkOAuthAccountCommand(
            user_id=self.user_id,
            provider=self.provider,
            provider_user_id=user.id,
            email=user.email,
        )

    @classmethod
    async def run(cls, user_id: UUID, command: VerifyIDTokenCommand) -> Self:
        return await cls(user_id, command.provider).pipeline(command)
```

The initial `VerifyIDTokenCommand` only carries the token. Once the OAuth identity is verified, the seeded `user_id` (taken from the auth context) is used by the step that builds `LinkOAuthAccountCommand`. `provider` is read from the input command, so callers only pass `user_id` and the command to `run`.

### Middlewares

A pipeline accepts middlewares with `add_middlewares`, with the same syntax as a bus (see [Middlewares](middlewares.md)):

```python
class PaymentContext:
    pipeline = ContextCommandPipeline().add_middlewares(
        timing_middleware,
        transaction_middleware,
    )
```

Pipeline middlewares wrap the whole run, not each step, and receive the initial command. The middlewares configured on the underlying `CommandBus` still apply to every command the pipeline dispatches.
