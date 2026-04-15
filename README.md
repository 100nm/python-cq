# python-cq

[![CI](https://github.com/100nm/python-cq/actions/workflows/ci.yml/badge.svg)](https://github.com/100nm/python-cq)
[![PyPI - Version](https://img.shields.io/pypi/v/python-cq.svg?color=blue)](https://pypi.org/project/python-cq)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/python-cq.svg?color=blue)](https://pypistats.org/packages/python-cq)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Documentation: https://python-cq.remimd.dev

**python-cq** is a Python package designed to organize your code following CQRS principles. It provides a `DIAdapter` protocol for dependency injection, with [python-injection](https://github.com/100nm/python-injection) as the default implementation available via the `[injection]` extra.

## Installation

⚠️ _Requires Python 3.12 or higher_

Without dependency injection:
```bash
pip install python-cq
```

With [python-injection](https://github.com/100nm/python-injection) as the DI backend (recommended):
```bash
pip install "python-cq[injection]"
```
