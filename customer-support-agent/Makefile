.DEFAULT_GOAL := help
PY ?= python

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install package + dev tools (editable)
	$(PY) -m pip install -e ".[dev,llm,ui]"

install-rag: ## Install the retrieval stack (embeddings, vector store, PDF)
	$(PY) -m pip install -e ".[rag]"

lint: ## Lint and check formatting
	ruff check . && ruff format --check .

format: ## Auto-fix lint issues and format
	ruff check --fix . && ruff format .

test: ## Run unit tests with coverage
	pytest --cov

orders: ## Generate ~100 synthetic orders into var/orders.json
	$(PY) scripts/generate_orders.py --n 100 --seed 42 --out var/orders.json

ingest: ## Chunk + embed kb/ into the vector store
	$(PY) -m scripts.ingest_kb

run: ## Run the Chat API locally with auto-reload
	uvicorn services.chat_api.main:app --reload --port 8000

up: ## Start all services with Docker Compose
	docker compose up -d --build

down: ## Stop all services
	docker compose down

eval: ## Run the full eval harness against the running API
	$(PY) eval/run_eval.py --dataset eval/datasets/v0 --api-url http://localhost:8000

eval-ci: ## Run the reduced eval in-process with the mock LLM (used by CI)
	$(PY) eval/run_eval.py --dataset eval/datasets/v0 --in-process --limit 20

.PHONY: help install install-rag lint format test orders ingest run up down eval eval-ci
