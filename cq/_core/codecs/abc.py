from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class Encoder[Plain, Encoded](Protocol):
    __slots__ = ()

    @abstractmethod
    def encode(self, value: Plain, /) -> Encoded:
        raise NotImplementedError


@runtime_checkable
class Decoder[Plain, Encoded](Protocol):
    __slots__ = ()

    @abstractmethod
    def decode(self, value: Encoded, /) -> Plain:
        raise NotImplementedError


@runtime_checkable
class Codec[Plain, Encoded](Encoder[Plain, Encoded], Decoder[Plain, Encoded], Protocol):
    __slots__ = ()
