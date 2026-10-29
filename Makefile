SHELL := /usr/bin/env bash
POETRY ?= poetry
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show the help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: format
format: ## Format code with ruff
	$(POETRY) run ruff check --fix
	$(POETRY) run ruff format

.PHONY: lint
lint: ## Run linting checks (ruff, flake8)
	$(POETRY) run ruff check --exit-non-zero-on-fix
	$(POETRY) run ruff format --check --diff
	$(POETRY) run flake8 .

.PHONY: type-check
type-check: ## Run type checking (mypy)
	$(POETRY) run mypy classes
	$(POETRY) run mypy tests

.PHONY: unit
unit: ## Run unit tests with pytest (incl. doctests in classes, docs/pages and README.md)
	$(POETRY) run pytest classes tests docs/pages README.md

.PHONY: typesafety
typesafety: ## Run type-safety tests with pytest-mypy-plugins (PYTEST_EXTRA_ARGS for sharding, etc)
	$(POETRY) run pytest typesafety $(PYTEST_EXTRA_ARGS) \
	  -p no:cov -o addopts="" --mypy-ini-file=setup.cfg

.PHONY: docs
docs: ## Check documentation (doc8, codespell)
	$(POETRY) run doc8 -q docs
	$(POETRY) run codespell classes tests docs typesafety README.md CONTRIBUTING.md CHANGELOG.md

.PHONY: package
package: ## Check the package integrity (poetry check, pip check, safety)
	$(POETRY) check
	$(POETRY) run pip check
	$(POETRY) run safety check --full-report

.PHONY: install
install: ## Install the project and all dev documentation dependencies
	$(POETRY) install

.PHONY: update
update: ## Re-lock and re-install all dependencies
	$(POETRY) lock
	$(POETRY) install

.PHONY: clean
clean: ## Remove caches, coverage output and build artifacts
	rm -rf .pytest_cache .mypy_cache .coverage coverage.xml htmlcov build dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: test
test: lint type-check unit typesafety docs package ## Run all checks (lint, type-check, unit, typesafety, docs, package)