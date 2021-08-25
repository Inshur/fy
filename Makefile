APP=fycli
VERSION := $(shell python -c 'import toml; print(toml.load("pyproject.toml")["tool"]["poetry"]["version"])')

clean:
	@rm -vrf ${APP}.egg-info venv build dist venv

install:
	pip install fycli

build-deps:
	pip install --upgrade build twine poetry

build: build-deps
	python -m build

push: clean build
	twine upload dist/*

dev:
	@poetry run ${APP}

venv:
	@virtualenv venv
	@echo "# run:"
	@echo "source venv/bin/activate"

version:
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

version-show:
	@echo ${VERSION}
