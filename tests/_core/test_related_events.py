import pytest

from cq import AnyIORelatedEvents


class TestAnyIORelatedEvents:
    async def test_add_with_success_emits_events(self) -> None:
        emitted = []

        async def emit(event: object) -> None:
            emitted.append(event)

        async with AnyIORelatedEvents(emit) as related_events:
            related_events.add("first", "second")

        assert emitted == ["first", "second"]
        assert related_events.history == ["first", "second"]

    async def test_aexit_with_body_error_raises_error_and_emits_added_events(
        self,
    ) -> None:
        emitted = []

        async def emit(event: object) -> None:
            emitted.append(event)

        with pytest.raises(ValueError, match="body"):
            async with AnyIORelatedEvents(emit) as related_events:
                related_events.add("event")
                raise ValueError("body")

        assert emitted == ["event"]

    async def test_bool_without_events_returns_false(self) -> None:
        async def emit(event: object) -> None: ...

        async with AnyIORelatedEvents(emit) as related_events:
            assert not related_events

    async def test_bool_with_events_returns_true(self) -> None:
        async def emit(event: object) -> None: ...

        async with AnyIORelatedEvents(emit) as related_events:
            related_events.add("event")
            assert related_events
