from dataclasses import dataclass

import pytest
from typing_extensions import TypeForm

from cq import Codec, Envelope, PolymorphicCodec, meta
from cq.exceptions import (
    DuplicateTypeNameError,
    MissingTypeNameError,
    UnknownTypeNameError,
)
from cq.ext.pydantic import PydanticCodec


@dataclass(frozen=True, slots=True)
class _Created:
    name: str


@dataclass(frozen=True, slots=True)
class _Deleted:
    reason: str


@meta("renamed")
@dataclass(frozen=True, slots=True)
class _Renamed:
    name: str


@meta()
@dataclass(frozen=True, slots=True)
class _Anonymous:
    name: str


type _Event = _Created | _Deleted


def _resolve_name(type_: type) -> str:
    return type_.__name__


class TestPolymorphicCodec:
    def test_encode_with_value_returns_envelope_named_after_its_type(self) -> None:
        codec = PolymorphicCodec(
            (_Created, _Deleted),
            PydanticCodec.from_type,
            name_resolver=_resolve_name,
        )

        encoded = codec.encode(_Deleted(reason="obsolete"))

        assert encoded == Envelope("_Deleted", b'{"reason":"obsolete"}')

    @pytest.mark.parametrize(
        "value",
        [_Created(name="a"), _Deleted(reason="obsolete")],
    )
    def test_decode_with_encoded_value_returns_equal_value(
        self,
        value: _Event,
    ) -> None:
        codec = PolymorphicCodec(
            (_Created, _Deleted),
            PydanticCodec.from_type,
            name_resolver=_resolve_name,
        )
        encoded = codec.encode(value)

        decoded = codec.decode(encoded)

        assert decoded == value

    def test_decode_with_unknown_type_name_raises_unknown_type_name_error(
        self,
    ) -> None:
        codec = PolymorphicCodec(
            (_Created,),
            PydanticCodec.from_type,
            name_resolver=_resolve_name,
        )

        with pytest.raises(UnknownTypeNameError):
            codec.decode(Envelope("_Deleted", b'{"reason":"obsolete"}'))

    def test_decode_with_type_added_after_first_decode_returns_value(self) -> None:
        types: list[type[_Event]] = [_Created]
        codec = PolymorphicCodec(
            types,
            PydanticCodec.from_type,
            name_resolver=_resolve_name,
        )
        codec.decode(Envelope("_Created", b'{"name":"a"}'))
        types.append(_Deleted)

        decoded = codec.decode(Envelope("_Deleted", b'{"reason":"obsolete"}'))

        assert decoded == _Deleted(reason="obsolete")

    def test_decode_with_types_sharing_a_name_raises_duplicate_type_name_error(
        self,
    ) -> None:
        codec = PolymorphicCodec(
            (_Created, _Deleted),
            PydanticCodec.from_type,
            name_resolver=lambda _: "event",
        )

        with pytest.raises(DuplicateTypeNameError):
            codec.decode(Envelope("event", b'{"name":"a"}'))

    def test_encode_with_same_type_twice_builds_its_codec_once(self) -> None:
        built: list[TypeForm[object]] = []

        def codec_factory[T](type_: TypeForm[T]) -> Codec[T, bytes]:
            built.append(type_)
            return PydanticCodec.from_type(type_)

        codec = PolymorphicCodec(
            (_Created,),
            codec_factory,
            name_resolver=_resolve_name,
        )
        codec.encode(_Created(name="a"))

        codec.encode(_Created(name="b"))

        assert built == [_Created]

    def test_encode_with_meta_decorated_type_returns_envelope_named_after_its_meta(
        self,
    ) -> None:
        codec = PolymorphicCodec((_Renamed,), PydanticCodec.from_type)

        encoded = codec.encode(_Renamed(name="a"))

        assert encoded == Envelope("renamed", b'{"name":"a"}')

    @pytest.mark.parametrize("value", [_Created(name="a"), _Anonymous(name="a")])
    def test_encode_without_type_name_raises_missing_type_name_error(
        self,
        value: _Created | _Anonymous,
    ) -> None:
        codec = PolymorphicCodec((type(value),), PydanticCodec.from_type)

        with pytest.raises(MissingTypeNameError):
            codec.encode(value)
