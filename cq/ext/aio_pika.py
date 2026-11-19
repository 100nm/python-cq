from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractExchange, AbstractIncomingMessage, AbstractQueue

from cq import Consumer, Decoder, Delivery, Encoder, Envelope, Producer, meta
from cq.exceptions import MalformedMessageError

__all__ = ("RabbitMQConsumer", "RabbitMQProducer")


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class RabbitMQProducer[T](Producer[T]):
    exchange: AbstractExchange
    encoder: Encoder[T, Envelope[bytes]]
    app_id: str | None = field(default=None)
    correlation_id_resolver: Callable[[T], str | None] = field(
        default=lambda message: meta.of(message).stringify_correlation_id(message),
    )

    async def send(self, message: T, /) -> None:
        envelope = self.encoder.encode(message)
        await self.exchange.publish(
            Message(
                envelope.body,
                app_id=self.app_id,
                correlation_id=self.correlation_id_resolver(message),
                delivery_mode=DeliveryMode.PERSISTENT,
                type=envelope.type,
            ),
            routing_key=envelope.type,
        )


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class RabbitMQConsumer[T](Consumer[T]):
    queue: AbstractQueue
    decoder: Decoder[T, Envelope[bytes]]

    async def __aiter__(self) -> AsyncIterator[Delivery[T]]:
        async with self.queue.iterator() as messages:
            async for message in messages:
                yield self.__deliver(message)

    @asynccontextmanager
    async def __deliver(self, message: AbstractIncomingMessage) -> AsyncIterator[T]:
        async with message.process():
            if message.type is None:
                raise MalformedMessageError("The message has no type.")

            envelope = Envelope(message.type, message.body)
            yield self.decoder.decode(envelope)
