from collections.abc import Iterator
from typing import ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cq import command_handler
from cq.ext.fastapi import DeferredCommandBus

app = FastAPI()


class DeferredCommand: ...


@command_handler
class DeferredCommandHandler:
    call_count: ClassVar[int] = 0

    async def handle(self, command: DeferredCommand) -> None:
        DeferredCommandHandler.call_count += 1


@app.post("/defer", status_code=204)
async def defer(bus: DeferredCommandBus) -> None:
    command = DeferredCommand()
    await bus.defer(command)


class TestFastAPIDeferredBus:
    @pytest.fixture(scope="class")
    def client(self) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client

    def test_defer_with_deferred_command_bus(self, client: TestClient) -> None:
        response = client.post("/defer")
        assert response.status_code == 204
        assert DeferredCommandHandler.call_count == 1
