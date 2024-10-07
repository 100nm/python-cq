from abc import ABC
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class DTO(BaseModel, ABC):
    __slots__ = ()

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
