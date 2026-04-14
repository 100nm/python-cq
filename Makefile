before_commit: lint mypy pytest

install:
	uv sync --all-extras

update:
	uv lock --upgrade
	uv sync --all-extras

lint:
	uv run ruff format
	uv run ruff check --fix

mypy:
	uv run mypy ./

pytest:
	uv run pytest

mkdocs:
	uv run mkdocs serve
