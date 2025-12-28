# python-cq

[![PyPI - Version](https://img.shields.io/pypi/v/python-cq.svg?color=4051b5&style=for-the-badge)](https://pypi.org/project/python-cq)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/python-cq.svg?color=4051b5&style=for-the-badge)](https://pypistats.org/packages/python-cq)

**python-cq** is a Python package designed to organize your code following CQRS principles. It builds on top of [python-injection](https://github.com/100nm/python-injection) for dependency injection.

## What is CQRS?

CQRS (Command Query Responsibility Segregation) is an architectural pattern that separates read operations from write operations. This separation helps to:

- **Clarify intent**: each operation has a single, well-defined responsibility
- **Improve maintainability**: smaller, focused handlers are easier to understand and modify
- **Simplify testing**: isolated handlers are straightforward to unit test

CQRS is often associated with distributed systems and Event Sourcing, but its benefits extend beyond that. Even in a local or monolithic application, adopting this pattern helps structure your code and makes the boundaries between reading and writing explicit.

## Prerequisites

To get the most out of **python-cq**, familiarity with the following concepts is recommended:

- **CQRS** and the distinction between Commands, Queries and Events
- **Domain Driven Design (DDD)**, particularly aggregates and bounded contexts

This knowledge will help you design coherent handlers and organize your code effectively.

## Message types

**python-cq** provides three types of messages to model your application's operations:

- **Command**: represents an intent to change the system's state. A command is handled by exactly one handler and may return a value for convenience.
- **Query**: represents a request for information. A query is handled by exactly one handler and returns data without side effects.
- **Event**: represents something that has happened in the system. An event can be handled by zero, one, or many handlers, enabling loose coupling between components.

## Installation

Requires Python 3.12 or higher.
```bash
pip install python-cq
```
