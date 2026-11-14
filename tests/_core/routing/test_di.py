import pytest

from cq._core.routing.di import NoDI


class _Service: ...


class TestNoDI:
    def test_command_scope_with_success_returns_none(self) -> None:
        assert NoDI().command_scope() is None

    def test_lazy_with_any_type_raises_runtime_error(self) -> None:
        with pytest.raises(RuntimeError, match="Can't lazily resolve _Service"):
            NoDI().lazy(_Service)

    async def test_wire_with_success_returns_factory_instantiating_type(self) -> None:
        factory = NoDI().wire(_Service)

        assert isinstance(await factory(), _Service)
