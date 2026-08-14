# Requirements Discovery Copilot — task runner
# Usage: `make <target>`. Run `make help` for the list.

SHELL := /bin/bash
API_DIR := apps/api
WEB_DIR := apps/web

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# --- Docker Compose -------------------------------------------------------
.PHONY: up
up: ## Start the full stack (db + api + web)
	docker compose up --build -d

.PHONY: up-redis
up-redis: ## Start the stack including the optional redis profile
	docker compose --profile redis up --build -d

.PHONY: down
down: ## Stop the stack
	docker compose down

.PHONY: logs
logs: ## Tail all service logs
	docker compose logs -f

# --- Backend --------------------------------------------------------------
.PHONY: api-install
api-install: ## Install API dependencies (editable + dev extras)
	cd $(API_DIR) && pip install -e ".[dev]"

.PHONY: migrate
migrate: ## Apply database migrations
	cd $(API_DIR) && alembic upgrade head

.PHONY: seed
seed: ## Seed the warehouse-modernization demo session
	cd $(API_DIR) && python -m app.seed

.PHONY: api
api: ## Run the API locally with autoreload
	cd $(API_DIR) && uvicorn app.main:app --reload

.PHONY: export
export: ## Export the seeded session's discovery package
	cd $(API_DIR) && python -m app.scripts.export_demo

# --- Frontend -------------------------------------------------------------
.PHONY: web-install
web-install: ## Install web dependencies
	cd $(WEB_DIR) && npm install

.PHONY: web
web: ## Run the web app locally
	cd $(WEB_DIR) && npm run dev

# --- Quality --------------------------------------------------------------
.PHONY: lint
lint: ## Lint backend (ruff + mypy) and frontend (eslint + tsc)
	cd $(API_DIR) && ruff check . && mypy app
	cd $(WEB_DIR) && npm run lint && npm run typecheck

.PHONY: format
format: ## Auto-format backend and frontend
	cd $(API_DIR) && ruff format . && ruff check --fix .
	cd $(WEB_DIR) && npm run format

.PHONY: test
test: ## Run all tests
	cd $(API_DIR) && pytest
	cd $(WEB_DIR) && npm test --silent

.PHONY: e2e
e2e: ## Run the end-to-end discovery scenario
	cd $(API_DIR) && pytest tests/e2e -v

.PHONY: precommit
precommit: ## Run all configured pre-commit hooks
	pre-commit run --all-files
