from collections.abc import AsyncIterator, Iterator
from contextlib import suppress
from dataclasses import dataclass
from uuid import UUID, uuid4

import aio_pika
import anyio
import pytest
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
)
from testcontainers.community.rabbitmq import RabbitMqContainer

from cq import PolymorphicCodec, meta
from cq.exceptions import MalformedMessageError, UnknownTypeNameError
from cq.ext.aio_pika import RabbitMQConsumer, RabbitMQProducer
from cq.ext.pydantic import PydanticCodec


@meta("created")
@dataclass(frozen=True, slots=True)
class _Created:
    name: str
    correlation_id: UUID | None = None


@meta("renamed", correlation_id_field="request_id")
@dataclass(frozen=True, slots=True)
class _Renamed:
    name: str
    request_id: UUID


@meta("deleted")
@dataclass(frozen=True, slots=True)
class _Deleted:
    reason: str


type _Message = _Created | _Renamed | _Deleted


@pytest.fixture(scope="session")
def rabbitmq() -> Iterator[RabbitMqContainer]:
    with RabbitMqContainer("rabbitmq:alpine") as container:
        yield container


@pytest.fixture
async def connection(rabbitmq: RabbitMqContainer) -> AsyncIterator[AbstractConnection]:
    connection = await aio_pika.connect(
        host=rabbitmq.get_container_host_ip(),
        port=int(rabbitmq.get_exposed_port(rabbitmq.port)),
        login=rabbitmq.username,
        password=rabbitmq.password,
        virtualhost=rabbitmq.vhost,
    )

    async with connection:
        yield connection


@pytest.fixture
async def channel(connection: AbstractConnection) -> AbstractChannel:
    return await connection.channel()


@pytest.fixture
async def exchange(channel: AbstractChannel) -> AbstractExchange:
    return await channel.declare_exchange(
        f"cq-tests-{uuid4()}",
        ExchangeType.DIRECT,
        auto_delete=True,
    )


@pytest.fixture
async def dead_letters(channel: AbstractChannel) -> AbstractQueue:
    return await channel.declare_queue(exclusive=True)


@pytest.fixture
async def queue(
    channel: AbstractChannel,
    exchange: AbstractExchange,
    dead_letters: AbstractQueue,
) -> AbstractQueue:
    queue = await channel.declare_queue(
        exclusive=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": dead_letters.name,
        },
    )

    for routing_key in ("created", "renamed", "deleted"):
        await queue.bind(exchange, routing_key=routing_key)

    return queue


@pytest.fixture
def codec() -> PolymorphicCodec[_Message, bytes]:
    return PolymorphicCodec(
        (_Created, _Renamed, _Deleted),
        PydanticCodec.from_type,
    )


@pytest.fixture
def producer(
    exchange: AbstractExchange,
    codec: PolymorphicCodec[_Message, bytes],
) -> RabbitMQProducer[_Message]:
    return RabbitMQProducer(exchange, codec)


@pytest.fixture
def consumer(
    queue: AbstractQueue,
    codec: PolymorphicCodec[_Message, bytes],
) -> RabbitMQConsumer[_Message]:
    return RabbitMQConsumer(queue, codec)


async def _receive(queue: AbstractQueue) -> AbstractIncomingMessage:
    with anyio.fail_after(5):
        async with queue.iterator(no_ack=True) as messages:
            return await anext(messages)


class TestRabbitMQProducer:
    async def test_send_with_message_publishes_body_routed_by_type(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
    ) -> None:
        await producer.send(_Deleted(reason="obsolete"))

        message = await _receive(queue)

        assert message.body == b'{"reason":"obsolete"}'
        assert message.type == "deleted"
        assert message.routing_key == "deleted"

    async def test_send_with_message_publishes_persistent_message(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
    ) -> None:
        await producer.send(_Deleted(reason="obsolete"))

        message = await _receive(queue)

        assert message.delivery_mode == DeliveryMode.PERSISTENT

    async def test_send_with_app_id_publishes_app_id(
        self,
        exchange: AbstractExchange,
        codec: PolymorphicCodec[_Message, bytes],
        queue: AbstractQueue,
    ) -> None:
        producer = RabbitMQProducer(exchange, codec, app_id="cq-tests")

        await producer.send(_Deleted(reason="obsolete"))

        message = await _receive(queue)

        assert message.app_id == "cq-tests"

    async def test_send_without_app_id_publishes_no_app_id(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
    ) -> None:
        await producer.send(_Deleted(reason="obsolete"))

        message = await _receive(queue)

        assert message.app_id is None

    async def test_send_with_correlation_id_attribute_publishes_correlation_id(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
    ) -> None:
        correlation_id = uuid4()

        await producer.send(_Created(name="a", correlation_id=correlation_id))

        message = await _receive(queue)

        assert message.correlation_id == str(correlation_id)

    async def test_send_without_correlation_id_publishes_no_correlation_id(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
    ) -> None:
        await producer.send(_Deleted(reason="obsolete"))

        message = await _receive(queue)

        assert message.correlation_id is None

    async def test_send_with_correlation_id_field_publishes_field_value(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
    ) -> None:
        request_id = uuid4()

        await producer.send(_Renamed(name="b", request_id=request_id))

        message = await _receive(queue)

        assert message.correlation_id == str(request_id)

    async def test_send_with_correlation_id_resolver_publishes_resolved_value(
        self,
        exchange: AbstractExchange,
        codec: PolymorphicCodec[_Message, bytes],
        queue: AbstractQueue,
    ) -> None:
        producer = RabbitMQProducer(
            exchange,
            codec,
            correlation_id_resolver=lambda message: "resolved",
        )

        await producer.send(_Deleted(reason="obsolete"))

        message = await _receive(queue)

        assert message.correlation_id == "resolved"

    async def test_call_with_message_publishes_message(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
    ) -> None:
        await producer(_Deleted(reason="obsolete"))

        message = await _receive(queue)

        assert message.body == b'{"reason":"obsolete"}'


class TestRabbitMQConsumer:
    async def test_aiter_with_sent_messages_yields_decoded_messages(
        self,
        producer: RabbitMQProducer[_Message],
        consumer: RabbitMQConsumer[_Message],
    ) -> None:
        sent: list[_Message] = [_Created(name="a"), _Deleted(reason="obsolete")]
        received = []

        for message in sent:
            await producer.send(message)

        async for delivery in consumer:
            async with delivery as message:
                received.append(message)

            if len(received) == len(sent):
                break

        assert received == sent

    async def test_aiter_with_success_acks_message(
        self,
        producer: RabbitMQProducer[_Message],
        consumer: RabbitMQConsumer[_Message],
        connection: AbstractConnection,
        channel: AbstractChannel,
        queue: AbstractQueue,
    ) -> None:
        await producer.send(_Created(name="a"))

        async for delivery in consumer:
            async with delivery:
                break

        await channel.close()
        other_channel = await connection.channel()
        declared = await other_channel.declare_queue(queue.name, passive=True)

        assert declared.declaration_result.message_count == 0

    async def test_aiter_with_error_in_delivery_raises_error_and_rejects_message(
        self,
        producer: RabbitMQProducer[_Message],
        consumer: RabbitMQConsumer[_Message],
        dead_letters: AbstractQueue,
    ) -> None:
        await producer.send(_Created(name="a"))

        with pytest.raises(ValueError, match="handler failed"):
            async for delivery in consumer:
                async with delivery:
                    raise ValueError("handler failed")

        dead_letter = await _receive(dead_letters)

        assert dead_letter.body == b'{"name":"a","correlation_id":null}'

    async def test_aiter_without_type_raises_malformed_message_error(
        self,
        exchange: AbstractExchange,
        consumer: RabbitMQConsumer[_Message],
        dead_letters: AbstractQueue,
    ) -> None:
        await exchange.publish(Message(b"{}"), routing_key="created")

        with pytest.raises(MalformedMessageError):
            async for delivery in consumer:
                async with delivery:
                    pass

        dead_letter = await _receive(dead_letters)

        assert dead_letter.body == b"{}"

    async def test_aiter_with_unknown_type_raises_unknown_type_name_error(
        self,
        exchange: AbstractExchange,
        consumer: RabbitMQConsumer[_Message],
        dead_letters: AbstractQueue,
    ) -> None:
        await exchange.publish(Message(b"{}", type="unknown"), routing_key="created")

        with pytest.raises(UnknownTypeNameError):
            async for delivery in consumer:
                async with delivery:
                    pass

        dead_letter = await _receive(dead_letters)

        assert dead_letter.type == "unknown"

    async def test_aiter_with_error_calls_on_error_with_error_and_message(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
        codec: PolymorphicCodec[_Message, bytes],
    ) -> None:
        errors = []

        async def on_error(
            exc: BaseException,
            message: AbstractIncomingMessage,
        ) -> None:
            errors.append((exc, message.body))
            await message.reject(requeue=False)

        consumer = RabbitMQConsumer(queue, codec, on_error=on_error)
        error = ValueError("handler failed")

        await producer.send(_Deleted(reason="obsolete"))

        with pytest.raises(ValueError, match="handler failed"):
            async for delivery in consumer:
                async with delivery:
                    raise error

        assert errors == [(error, b'{"reason":"obsolete"}')]

    async def test_aiter_with_requeueing_on_error_redelivers_message(
        self,
        producer: RabbitMQProducer[_Message],
        queue: AbstractQueue,
        codec: PolymorphicCodec[_Message, bytes],
    ) -> None:
        async def on_error(
            exc: BaseException,
            message: AbstractIncomingMessage,
        ) -> None:
            await message.reject(requeue=not message.redelivered)

        consumer = RabbitMQConsumer(queue, codec, on_error=on_error)
        sent = _Created(name="a")
        received = []

        await producer.send(sent)

        async for delivery in consumer:
            with suppress(ValueError):
                async with delivery as message:
                    received.append(message)

                    if len(received) == 1:
                        raise ValueError("first attempt failed")

            if len(received) == 2:
                break

        assert received == [sent, sent]

    async def test_aiter_with_cancellation_leaves_message_unacknowledged(
        self,
        producer: RabbitMQProducer[_Message],
        consumer: RabbitMQConsumer[_Message],
        connection: AbstractConnection,
        channel: AbstractChannel,
        queue: AbstractQueue,
    ) -> None:
        processing = anyio.Event()

        async def consume() -> None:
            async for delivery in consumer:
                async with delivery:
                    processing.set()
                    await anyio.sleep_forever()

        await producer.send(_Created(name="a"))

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(consume)
            await processing.wait()
            task_group.cancel_scope.cancel()

        await channel.close()
        other_channel = await connection.channel()
        declared = await other_channel.declare_queue(queue.name, passive=True)

        assert declared.declaration_result.message_count == 1
