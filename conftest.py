import pytest
from injection import Module

from cq import Router
from cq.ext.injection import InjectionAdapter


@pytest.fixture
def injection_module() -> Module:
    return Module()


@pytest.fixture
def router(injection_module: Module) -> Router:
    return Router(InjectionAdapter(injection_module)).register_defaults()
