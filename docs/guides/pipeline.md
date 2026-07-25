# Executing multiple commands

In CQRS, the saga pattern is typically used to orchestrate a sequence of commands. Sagas are designed for distributed systems and can feel overengineered for a local workflow. **python-cq** offers `ContextCommandPipeline` as a lightweight alternative for chaining commands in-process.

## Pipeline basics

A pipeline runs a sequence of commands. Each step receives the result of the previous command and produces the next command to dispatch. The pipeline itself is the context: instance attributes you assign in one step are visible in the next.

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

`ContextCommandPipeline()` uses the default `CQ` instance. If you manage your own `CQ` (see [Custom DI adapter](../di.md)), pass its DI adapter explicitly: `ContextCommandPipeline(cq.di)`.

## Steps

A step is a method decorated with `@pipeline.step`. It receives the value returned by the previous command's handler and returns the next command to dispatch. Step methods can be either sync or async.

A step that returns `None` stops the pipeline immediately. This is the natural way to write a terminal step that only consumes the previous result without producing another command, and it also lets earlier steps abort the pipeline conditionally:

```python
@pipeline.step
def _(self, result: ValidationResult):
    if result.is_valid:
        return PersistCommand(...)

    return None  # stop here, skip the rest of the pipeline
```

### Dispatching queries

`@pipeline.query_step` works the same way as `@pipeline.step` but dispatches its produced message through the `QueryBus` instead of the `CommandBus`:

```python
@pipeline.query_step
def _(self, result: TransactionCreatedResult) -> GetMerchantByIdQuery:
    return GetMerchantByIdQuery(merchant_id=result.merchant_id)
```

### Static steps

If a step does not depend on the previous result, declare it with `add_static_step` (for commands) or `add_static_query_step` (for queries). The given message is dispatched as-is each time the pipeline runs:

```python
class WarmCachePipeline:
    pipeline: ContextCommandPipeline[StartCommand] = ContextCommandPipeline()

    pipeline.add_static_step(LoadConfigCommand())
    pipeline.add_static_query_step(GetActiveUsersQuery())

    @pipeline.step
    def _(self, users: list[User]) -> WarmCacheCommand:
        return WarmCacheCommand(user_ids=[u.id for u in users])
```

Static steps and decorated steps are interleaved in the order they are declared in the class body.

## Running a pipeline

Instantiating the pipeline is implicit: calling `Context.pipeline(initial_command)` builds a fresh `Context` instance, runs every step against it, and returns the populated context.

```python
async def process_payment(cart_id: int) -> int:
    command = ValidateCartCommand(cart_id=cart_id)
    context = await PaymentContext.pipeline(command)
    return context.transaction_id
```

Each pipeline run gets its own context instance, so attributes you set in one run do not leak into the next.

### Seeding the context with base values

If a step needs values that are known before the first command runs, instantiate the context yourself and call `pipeline` on the instance. The same object is returned at the end, mutated by every step that ran.

Because the input context and the returned one are the same object, the recommended pattern is to centralize both calls behind a `run` classmethod:

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

The initial `VerifyIDTokenCommand` only depends on the token it carries. Once the OAuth identity is verified, the seeded `user_id` (taken from the auth context) is consumed by the step that builds `LinkOAuthAccountCommand`. `provider` is extracted from the input command, so callers only pass `user_id` and the command to `run`.

## Middlewares

A pipeline is itself a dispatcher. You can wrap it with middlewares the same way you would wrap a bus, using `add_middlewares`:

```python
class PaymentContext:
    pipeline = ContextCommandPipeline().add_middlewares(
        timing_middleware, retry_middleware
    )
    # ...
```

Middlewares wrap the whole pipeline execution, not each individual step. Individual command middlewares configured on the underlying `CommandBus` still apply to every command dispatched by the pipeline.
