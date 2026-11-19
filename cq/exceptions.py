__all__ = (
    "CQError",
    "CodecError",
    "DuplicateTypeNameError",
    "MalformedMessageError",
    "MiddlewareError",
    "MissingTypeNameError",
    "UnknownTypeNameError",
)


class CQError(Exception): ...


class MiddlewareError(CQError): ...


class MalformedMessageError(CQError): ...


class MissingTypeNameError(CQError): ...


class CodecError(CQError): ...


class UnknownTypeNameError(CodecError): ...


class DuplicateTypeNameError(CodecError): ...
