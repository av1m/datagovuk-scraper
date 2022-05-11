VENV := .venv
BIN := $(VENV)/bin
PYTHON := $(BIN)/python

.PHONY: help
help: ## Display callable targets.
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: format
format: ## Format all the project
	$(BIN)/docformatter --in-place -r **/*.py
	$(BIN)/isort --profile black .
	$(BIN)/black .

.PHONY: test
test: ## Test all the project
	$(BIN)/pylint datagovuk

.PHONY: install
install: ## This command must be launched for the first use of the project
	# Make a new virtual environment
	python3 -m venv $(VENV) && source $(BIN)/activate
	# Install dependencies
	$(BIN)/pip install --upgrade pip setuptools wheel
	$(BIN)/pip install -U -r requirements.txt