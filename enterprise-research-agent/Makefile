.DEFAULT_GOAL := help
PY ?= python

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (editable) + frontend deps
	cd backend && $(PY) -m pip install -e ".[dev]"
	cd frontend && npm ci

lint: ## Lint backend + frontend
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint && npm run typecheck

test: ## Backend unit tests with coverage (+ frontend unit tests)
	cd backend && pytest --cov -m "not integration"
	cd frontend && npm run test -- --run

test-integration: ## Backend integration tests (needs `make infra`)
	cd backend && pytest -m integration

infra: ## Start only PostgreSQL + Redis for local development
	docker compose up -d postgres redis

api: ## Run the API locally with auto-reload
	cd backend && alembic upgrade head && uvicorn app.main:app --reload --port 8000

worker: ## Run a worker locally
	cd backend && rq worker ingestion research --with-scheduler

web: ## Run the frontend dev server
	cd frontend && npm run dev

migration: ## Create a migration: make migration m="add reports table"
	cd backend && alembic revision --autogenerate -m "$(m)"

openapi: ## Regenerate docs/api/openapi.yaml (commit the result)
	cd backend && $(PY) scripts/export_openapi.py --out ../docs/api/openapi.yaml

up: ## Start the full stack
	docker compose up -d --build

down: ## Stop the full stack
	docker compose down

eval: ## Run the evaluation harness against the running stack
	$(PY) eval/run_eval.py --dataset eval/datasets/v0 --api-url http://localhost:8000

.PHONY: help install lint test test-integration infra api worker web migration openapi up down eval
