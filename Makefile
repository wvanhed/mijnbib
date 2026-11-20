dev: mdlint format lint testfast

init:
	uv sync

all: clean init mdlint format lint test check biblist

clean:
	rm -rf dist
	rm -rf src/*.egg-info
	rm -rf .venv

mdlint:
	uvx pymarkdownlnt scan --exclude CLAUDE.md .

lint:
	uv run ruff check .

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

# Validate built packages: metadata, and README rendering on PyPI
check: build
	uv run --with twine --no-project twine check --strict dist/*

# (uv publish is still experimental, so we still use twine)
# Always rebuilds first so dist/ can't contain stale artifacts from a
# previous (already-published) version.
publish: clean check
	# uv run --with twine --with setuptools --no-project twine upload --repository testpypi dist/*
	uv run --with twine --with setuptools --no-project twine upload dist/*

biblist:
	uv run python update_biblist.py
