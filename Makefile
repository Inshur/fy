APP=fycli
VERSION := $(shell python -c 'import toml; print(toml.load("pyproject.toml")["tool"]["poetry"]["version"])')

clean:
	@rm -vrf ${APP}.egg-info venv build dist

install:
	pip install fycli

build-deps:
	pip install --upgrade build twine toml dephell poetry

build: build-deps
	python -m build

push: build
	twine upload dist/*

dev:
	@poetry run ${APP}

venv:
	@virtualenv venv
	@echo "# run:"
	@echo "source venv/bin/activate"

setup:
	@dephell deps convert

version: setup
	$(shell echo "__version__ = \"${APP} ${VERSION}\"" > ${APP}/version.py)

version-patch:
	@poetry version patch
	@(make version)

version-minor:
	@poetry version minor
	@(make version)

version-major:
	@poetry version major
	@(make version)
