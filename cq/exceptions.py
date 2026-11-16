__all__ = (
    "CQError",
    "CodecError",
    "DuplicateTypeNameError",
    "MiddlewareError",
    "MissingTypeNameError",
    "UnknownTypeNameError",
)


class CQError(Exception): ...


class MiddlewareError(CQError): ...


class MissingTypeNameError(CQError): ...


class CodecError(CQError): ...


class UnknownTypeNameError(CodecError): ...


class DuplicateTypeNameError(CodecError): ...
