from typing import Any

from cq._core.routing.dispatchers.abc import Dispatcher


async def dispatch_sequentially[T, *Ts](
    dispatcher: Dispatcher[T, Any],
    /,
    *messages: T,
) -> tuple[*Ts]:
    return tuple([await dispatcher.dispatch(message) for message in messages])
