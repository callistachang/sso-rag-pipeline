ENV_NAME = sso-rag-pipeline
ENV_FILE = environment.yml
ENV_EXISTS := $(shell conda env list | grep -w $(ENV_NAME))

# Default target
.PHONY: all
all: create-env install-pre-commit-hooks

.PHONY: create-env
create-env:
ifndef ENV_EXISTS
	@echo "Creating conda environment..."
	conda env create --file $(ENV_FILE)
else
	@echo "Conda environment '$(ENV_NAME)' already exists. Skipping creation."
endif

.PHONY: pre-commit
pre-commit:
	@echo "Installing pre-commit hooks..."
	pre-commit install

.PHONY: update
update: $(ENV_FILE)
	@echo "Updating conda environment..."
	conda env update --file $(ENV_FILE) --prune

.PHONY: scrape
scrape:
	@echo "Running 'scrapy crawl sso'..."
	cd ./scrapers && scrapy crawl sso

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  make         - Create conda environment if doesn't exist and install pre-commit hooks"
	@echo "  make update  - Update the conda environment"
	@echo "  make help    - Display this help message"
	@echo "  make scrape  - Scrape latest SSO data"
