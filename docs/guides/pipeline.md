# Executing multiple commands

In CQRS, the saga pattern is typically used to orchestrate multiple commands. However, sagas are primarily designed for distributed systems and can feel overly complex in a local context.

**python-cq** provides the pipeline pattern as a simpler alternative for chaining commands locally.

## Pipeline

A pipeline executes a sequence of commands, where each step transforms the result of the previous command into the next command.

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
        return NotifyMerchantCommand(transaction_id=self.transaction_id)

    @pipeline.step
    def _(self, result: MerchantNotifiedResult):
        ...
```

The pipeline class acts as a context, allowing you to store intermediate values between steps.

### Steps

Each step is a method decorated with `@pipeline.step`. It receives the result of the previous command handler and returns the next command to dispatch.

You can also use `@pipeline.query_step` to dispatch queries instead of commands.

The last step is optional. If defined, it must return `None`.

### Dispatching a pipeline

To execute the pipeline, call `dispatch` with the initial command. It returns the context instance, giving you access to any values stored during execution.

```python
async def process_payment(cart_id: int) -> int:
    command = ValidateCartCommand(cart_id=cart_id)
    context = await PaymentContext.pipeline.dispatch(command)
    return context.transaction_id
```
