all: clean blackcheck test build

test:
	pytest -v
	python -m doctest src/mijnbib/mijnbibliotheek.py

black:
	isort --skip-glob="**/venv*" \
		  --profile=black \
		  .

	black -l 95 --exclude "venv*" .
	
# For CI/CD pipeline
blackcheck:
	isort --skip-glob="**/venv*" \
		  --profile=black \
		  --check \
		  .	
	black -l 95 --exclude "venv*" \
		  --check \
		  .

clean:
	rm -rf dist
	rm -rf src/*.egg-info
	
build:
	pip install --upgrade pip
	pip install --upgrade build
	python -m build

publish:
	python3 -m pip install --upgrade twine
	twine upload dist/*
