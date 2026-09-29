# python-cq

[![PyPI - Version](https://shieldcn.dev/pypi/v/python-cq.svg?color=3775A9&size=xs&variant=secondary)](https://pypi.org/project/python-cq)
[![PyPI - Downloads](https://shieldcn.dev/pypi/dm/python-cq.svg?color=3775A9&size=xs&variant=secondary)](https://pypistats.org/packages/python-cq)
[![GitHub Stars](https://shieldcn.dev/github/stars/100nm/python-cq.svg?size=xs&variant=secondary)](https://github.com/100nm/python-cq/stargazers)
[![CI](https://shieldcn.dev/github/ci/100nm/python-cq.svg?size=xs&variant=secondary&workflow=ci.yml)](https://github.com/100nm/python-cq/actions/workflows/ci.yml)
[![Ruff](https://shieldcn.dev/badge/code_style-Ruff-261230.svg?logo=ruff&size=xs&variant=secondary)](https://github.com/astral-sh/ruff)

An async-first Python library for structuring code around CQRS (Commands, Queries, Events) with pluggable dependency injection.

## Documentation

The full guide lives at **<https://python-cq.remimd.dev>**. Start there: it covers installation, the message model, dispatching, bus configuration, command pipelines, and how to plug in a custom DI framework.

## Installation

Requires Python 3.12 or higher.

```bash
pip install "python-cq[injection]"
```

The `[injection]` extra installs [python-injection](https://github.com/100nm/python-injection) as the default DI backend (recommended). To bring your own DI framework, install `python-cq` without the extra and see the [Custom DI adapter](https://python-cq.remimd.dev/di) guide.