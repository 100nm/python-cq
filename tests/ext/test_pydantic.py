from dataclasses import dataclass

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from cq import Codec
from cq.ext.pydantic import PydanticCodec, PydanticDecoder, PydanticEncoder


class _Model(BaseModel):
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class _Data:
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class _OtherData:
    label: str


class TestPydanticEncoder:
    def test_encode_with_base_model_returns_json_bytes(self) -> None:
        encoder = PydanticEncoder.from_type(_Model)

        encoded = encoder.encode(_Model(name="a", count=1))

        assert encoded == b'{"name":"a","count":1}'

    def test_encode_with_dataclass_returns_json_bytes(self) -> None:
        encoder = PydanticEncoder.from_type(_Data)

        encoded = encoder.encode(_Data(name="a", count=1))

        assert encoded == b'{"name":"a","count":1}'

    def test_from_type_with_class_returns_encoder(self) -> None:
        encoder = PydanticEncoder.from_type(_Model)

        assert type(encoder) is PydanticEncoder


class TestPydanticDecoder:
    def test_decode_with_valid_json_returns_instance(self) -> None:
        decoder = PydanticDecoder.from_type(_Model)

        decoded = decoder.decode(b'{"name":"a","count":1}')

        assert decoded == _Model(name="a", count=1)

    def test_decode_with_invalid_json_raises_validation_error(self) -> None:
        decoder = PydanticDecoder.from_type(_Model)

        with pytest.raises(ValidationError):
            decoder.decode(b'{"name":"a","count":"not a number"}')

    def test_decode_with_malformed_json_raises_validation_error(self) -> None:
        decoder = PydanticDecoder.from_type(_Model)

        with pytest.raises(ValidationError):
            decoder.decode(b"not json")

    def test_from_type_with_class_returns_decoder(self) -> None:
        decoder = PydanticDecoder.from_type(_Model)

        assert type(decoder) is PydanticDecoder


class TestPydanticCodec:
    def test_decode_with_encoded_value_returns_equal_value(self) -> None:
        codec = PydanticCodec.from_type(_Data)
        value = _Data(name="a", count=1)

        decoded = codec.decode(codec.encode(value))

        assert decoded == value

    def test_decode_with_union_adapter_returns_matching_type(self) -> None:
        codec: PydanticCodec[_Data | _OtherData] = PydanticCodec(
            TypeAdapter(_Data | _OtherData),
        )
        value = _OtherData(label="a")

        decoded = codec.decode(codec.encode(value))

        assert decoded == value

    def test_from_type_with_class_returns_codec(self) -> None:
        codec = PydanticCodec.from_type(_Model)

        assert type(codec) is PydanticCodec

    def test_isinstance_with_codec_protocol_returns_true(self) -> None:
        codec = PydanticCodec.from_type(_Model)

        assert isinstance(codec, Codec)
