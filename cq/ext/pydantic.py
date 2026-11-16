from dataclasses import dataclass
from typing import Self

from pydantic import TypeAdapter
from typing_extensions import TypeForm

from cq import Codec, Decoder, Encoder

__all__ = ("PydanticCodec", "PydanticDecoder", "PydanticEncoder")


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _PydanticAdapter[T]:
    adapter: TypeAdapter[T]

    @classmethod
    def from_type(cls, type_: TypeForm[T], /) -> Self:
        adapter = TypeAdapter(type_)
        return cls(adapter)


class PydanticEncoder[T](_PydanticAdapter[T], Encoder[T, bytes]):
    __slots__ = ()

    def encode(self, value: T, /) -> bytes:
        return self.adapter.dump_json(value)


class PydanticDecoder[T](_PydanticAdapter[T], Decoder[T, bytes]):
    __slots__ = ()

    def decode(self, value: bytes, /) -> T:
        return self.adapter.validate_json(value)


class PydanticCodec[T](PydanticEncoder[T], PydanticDecoder[T], Codec[T, bytes]):
    __slots__ = ()
