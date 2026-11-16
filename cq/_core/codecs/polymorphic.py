from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from typing import NamedTuple

from typing_extensions import TypeForm

from cq._core.codecs.abc import Codec
from cq._core.message import MessageTypeMetadata
from cq.exceptions import DuplicateTypeNameError, UnknownTypeNameError

type _CodecFactory[Plain, Encoded] = Callable[[TypeForm[Plain]], Codec[Plain, Encoded]]
type _TypeNameResolver[T] = Callable[[T], str]


class Envelope[T](NamedTuple):
    type: str
    body: T


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class PolymorphicCodec[Plain, Encoded](Codec[Plain, Envelope[Encoded]]):
    types: Collection[type[Plain]]
    codec_factory: _CodecFactory[Plain, Encoded]
    name_resolver: _TypeNameResolver[type[Plain]] = field(
        default=lambda type_: MessageTypeMetadata.of(type_).ensure_type_name(),
    )
    __codecs: dict[type[Plain], Codec[Plain, Encoded]] = field(
        default_factory=dict,
        init=False,
    )
    __types_by_name: dict[str, type[Plain]] = field(
        default_factory=dict,
        init=False,
    )

    def encode(self, value: Plain, /) -> Envelope[Encoded]:
        type_ = type(value)
        name = self.name_resolver(type_)
        body = self.__get_codec(type_).encode(value)
        return Envelope(name, body)

    def decode(self, value: Envelope[Encoded], /) -> Plain:
        type_ = self.__get_type(value.type)
        return self.__get_codec(type_).decode(value.body)

    def __get_codec(self, type_: type[Plain]) -> Codec[Plain, Encoded]:
        codec = self.__codecs.get(type_)

        if codec is None:
            codec = self.__codecs[type_] = self.codec_factory(type_)

        return codec

    def __get_type(self, name: str) -> type[Plain]:
        if name not in self.__types_by_name:
            self.__reindex()

        try:
            return self.__types_by_name[name]
        except KeyError as exc:
            raise UnknownTypeNameError(
                f"No type is registered under the name `{name}`.",
            ) from exc

    def __reindex(self) -> None:
        types = tuple(self.types)
        types_by_name = {self.name_resolver(type_): type_ for type_ in types}

        if len(types_by_name) != len(types):
            raise DuplicateTypeNameError("Several types share the same name.")

        self.__types_by_name.clear()
        self.__types_by_name.update(types_by_name)
