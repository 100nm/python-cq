__all__ = ("CQError", "MiddlewareError")


class CQError(Exception): ...


class MiddlewareError(CQError): ...
