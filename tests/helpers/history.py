from enum import IntEnum
from typing import Any, Mapping, NamedTuple

from cq import MiddlewareResult


class HistoryRecordStatus(IntEnum):
    SUCCESS = 1
    FAILED = 0


class HistoryRecord(NamedTuple):
    args: tuple[Any, ...]
    kwargs: Mapping[str, Any]
    result: Any
    status: HistoryRecordStatus

    @property
    def is_success(self) -> bool:
        return self.status == HistoryRecordStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status == HistoryRecordStatus.FAILED


class HistoryMiddleware:
    def __init__(self) -> None:
        self.__records: list[HistoryRecord] = []

    @property
    def records(self) -> tuple[HistoryRecord, ...]:
        return tuple(self.__records)

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        try:
            result = yield
        except BaseException as exc:
            record = HistoryRecord(args, kwargs, exc, HistoryRecordStatus.FAILED)
            raise exc
        else:
            record = HistoryRecord(args, kwargs, result, HistoryRecordStatus.SUCCESS)
        finally:
            self.__records.append(record)
