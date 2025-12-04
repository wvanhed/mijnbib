dev: format lint testfast

init:
	uv sync

all: clean init format lint test build biblist

clean:
	rm -rf dist
	rm -rf src/*.egg-info
	rm -rf .venv

lint:
	uv run ruff check .

black: format # legacy alias
format:
	uv run ruff check --select I . --fix 
	uv run ruff format .

# For CI/CD pipeline
formatcheck:
	uv run ruff check --select I .
	uv run ruff format --check .

test:
	uv run pytest -v
	uv run python -m doctest src/mijnbib/mijnbibliotheek.py
	uv run python -m doctest src/mijnbib/parsers.py
	uv run python -m doctest src/mijnbib/models.py

testfast:
	uv run pytest -k "not real"
	uv run python -m doctest src/mijnbib/mijnbibliotheek.py
	uv run python -m doctest src/mijnbib/parsers.py
	uv run python -m doctest src/mijnbib/models.py

build:
	uv build

# (uv publish is still experimental, so we still use twine)
publish:
	# uv run --with twine --with setuptools --no-project twine upload --repository testpypi dist/*
	uv run --with twine --with setuptools --no-project twine upload dist/*

biblist:
	uv run python update_biblist.py
