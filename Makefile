
.PHONY: help setup install test unit check lint

TEST_DIR = tests
DOCKER_REPO = registry.supercroy.com/updrytwist
DOCKER_PROJ = dlink-dschs150-hass
VERSION = $(shell poetry version | cut -d' ' -f2)

# Before working on something, run make bump-version-<major|minor|patch>
# When ready to commit, run make full-commit-ready or commit-ready for a faster commit
# To run a full build, run make full-build or fast-build for a faster build

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  setup             to setup project (not needed - template does this)"
	@echo "  poetry-config     to configure Poetry (only needed once per system)"
	@echo "  system-requirements-install    to install system requirements (only needed once per system)"
	@echo "  install           to install dependencies"
	@echo "  add-to-git        to add project to git"
	@echo "  first-make        to run install, add-to-git, full-commit-ready"
	@echo "  add-to-github     to add the project to github"
	@echo "  unit              to run unit tests"
	@echo "  check             to run pre-commit checks"
	@echo "  commit-ready      to run pre-commit checks and unit tests"
	@echo "  full-commit-ready to run pre-commit checks, unit tests, and bump version"
	@echo "  fast-build        to build with just unit tests and version bump"
	@echo "  max-build         to run a complete dependencies refresh, full build, and docker build/publish"
	@echo "  fast-docker-build to run the minimal docker build and publish"
	@echo "  publish-to-pypi   to publish to PyPI"
	@echo "  autoupdate        to update dependencies"
	@echo "  forced-update     to force update dependencies (clear Poetry cache)"
	@echo "  template-update   to run the copier update (latest template release)"
	@echo "  template-update-tip   to run the copier update (latest template tip)"
	@echo "  check-uncommitted to check for uncommitted changes in Git"
	@echo "  commit-and-tag-release    to commit and tag the release"
	@echo "  build-and-release-patch   to run the full build and release a patch"
	@echo "  build-and-release-minor   to run the full build and release a minor"
	@echo "  build-and-release-major   to run the full build and release a major"

setup:
	@poetry init
	@pre-commit install

poetry-config:
	@poetry config virtualenvs.in-project true
	@poetry config virtualenvs.create true
	@poetry config virtualenvs.path .venv

system-requirements-install:
	@winget install rhysd.actionlint koalaman.shellcheck mvdan.shfmt Gitleaks.Gitleaks Thoughtworks.Talisman waterlan.dos2unix GitHub.cli

install:
	@poetry install
	@poetry update

autoupdate:
	@poetry run pre-commit autoupdate
	@poetry update

forced-update:
	@poetry cache clear pypi --all
	@poetry run pre-commit autoupdate
	@poetry update

add-to-git:
	@git init
	@git add .
	@git add --chmod=+x run_scripts/*.sh
	@git commit -m "Initial commit from Copier template"
	@git config --global --add safe.directory $(CURDIR)
	@poetry run pre-commit install

add-to-github:
	@gh repo create dlink-dschs150-hass --public --source=.
	@git branch -M main
	@git remote add origin https://github.com/UpDryTwist/dlink-dschs150-hass.git
	@git push -u origin main

first-make: install add-to-git autoupdate full-commit-ready

just-unit:
	@poetry run pytest -s -v $(TEST_DIR)

unit:
	@poetry run coverage run -m pytest -s -v
	@poetry run coverage report -m
	@poetry run coverage html

check:
	@poetry run pre-commit run --all-files

check-manual:
	@poetry run pre-commit run --hook-stage manual --all-files

check-github-actions:
	@poetry run pre-commit run --hook-stage manual actionlint

commit-ready: check unit

full-commit-ready: autoupdate commit-ready check-manual

sphinx-start:
	@poetry run sphinx-quickstart docs

sphinx-build:
	@poetry run sphinx-build -b html docs docs/_build

publish-to-pypi:
	@poetry publish --build

build:
	@poetry build

docker-build-one:
	@docker build -t $(DOCKER_PROJ):$(VERSION) .

# You need to set up buildx. Run `docker buildx create --name mybuilder` and `docker buildx use mybuilder`
docker-build:
	@docker buildx build --platform linux/amd64,linux/arm64 \
		-t $(DOCKER_REPO)/$(DOCKER_PROJ):$(VERSION) \
		-t $(DOCKER_REPO)/$(DOCKER_PROJ):latest \
		--push .

docker-publish-one: docker-build-one
	@docker tag $(DOCKER_PROJ):$(VERSION) $(DOCKER_REPO)/$(DOCKER_PROJ):$(VERSION)
	@docker push $(DOCKER_REPO)/$(DOCKER_PROJ):$(VERSION)
	@docker tag $(DOCKER_PROJ):$(VERSION) $(DOCKER_REPO)/$(DOCKER_PROJ):latest
	@docker push $(DOCKER_REPO)/$(DOCKER_PROJ):latest

bump-version-major:
	@poetry run bump-my-version bump major pyproject.toml .bumpversion.toml
	@dos2unix .bumpversion.toml
	@dos2unix pyproject.toml

bump-version-minor:
	@poetry run bump-my-version bump minor pyproject.toml .bumpversion.toml
	@dos2unix .bumpversion.toml
	@dos2unix pyproject.toml

bump-version-patch:
	@poetry run bump-my-version bump patch pyproject.toml .bumpversion.toml
	@dos2unix .bumpversion.toml
	@dos2unix pyproject.toml

bump-version-pre:
	@poetry run bump-my-version bump pre_l pyproject.toml .bumpversion.toml
	@dos2unix .bumpversion.toml
	@dos2unix pyproject.toml

bump-version-build:
	@poetry run bump-my-version bump pre_n pyproject.toml .bumpversion.toml
	@dos2unix .bumpversion.toml
	@dos2unix pyproject.toml

version-build: bump-version-build build

fast-build: just-unit version-build

full-build: full-commit-ready version-build

max-build: autoupdate full-build docker-build

fast-docker-build: just-unit bump-version-build docker-publish-one

check-uncommitted:
	@if [ -n "$(shell git status --porcelain)" ]; then echo "Uncommitted changes in Git"; git status --short; exit 1; fi

commit-and-tag-release:
	@git add pyproject.toml .bumpversion.toml
	@git commit -m "Release version $(VERSION)"
	@git tag -a v$(VERSION) -m "Release version $(VERSION)"
	@git push origin main
	@git push origin v$(VERSION)

make-github-release:
	@gh release create v$(VERSION) --title "Release $(VERSION)" --notes "Release $(VERSION)"

pre-build-and-release-version: check-uncommitted autoupdate full-build docker-build-one

post-build-and-release-version: commit-and-tag-release make-github-release docker-publish-one

build-and-release-patch: pre-build-and-release-version bump-version-patch post-build-and-release-version

build-and-release-minor: pre-build-and-release-version bump-version-minor post-build-and-release-version

build-and-release-major: pre-build-and-release-version bump-version-major post-build-and-release-version

template-update:
	@copier update --trust --defaults --conflict inline

template-update-tip:
	@copier update --trust --defaults --conflict inline --vcs-ref=HEAD
