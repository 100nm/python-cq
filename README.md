# python-cq

[![CI](https://github.com/100nm/python-cq/actions/workflows/ci.yml/badge.svg)](https://github.com/100nm/python-cq)
[![PyPI - Version](https://img.shields.io/pypi/v/python-cq.svg?color=blue)](https://pypi.org/project/python-cq)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/python-cq.svg?color=blue)](https://pypistats.org/packages/python-cq)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An async-first Python library for structuring code around CQRS (Commands, Queries, Events) with pluggable dependency injection.

## Documentation

The full guide lives at **<https://python-cq.remimd.dev>**. Start there: it covers installation, the message model, dispatching, bus configuration, command pipelines, and how to plug in a custom DI framework.

## Installation

Requires Python 3.12 or higher.

```bash
pip install "python-cq[injection]"
```

The `[injection]` extra installs [python-injection](https://github.com/100nm/python-injection) as the default DI backend (recommended). To bring your own DI framework, install `python-cq` without the extra and see the [Custom DI adapter](https://python-cq.remimd.dev/di) guide.