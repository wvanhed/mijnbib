all: clean lint formatcheck test build

clean:
	rm -rf dist
	rm -rf src/*.egg-info

lint:
	ruff check .

black: format # legacy alias
format:
	ruff check --select I . --fix 
	ruff format .

# For CI/CD pipeline
formatcheck:
	ruff check --select I .
	ruff format --check .

test:
	pytest -v
	python -m doctest src/mijnbib/mijnbibliotheek.py
	python -m doctest src/mijnbib/parsers.py
	python -m doctest src/mijnbib/models.py

build:
	pip install --upgrade pip
	pip install --upgrade build
	python -m build

publish:
	python3 -m pip install --upgrade twine
	twine upload dist/*
