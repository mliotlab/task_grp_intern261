.DEFAULT_GOAL := help
PY ?= python

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install package + dev tools + dashboard (no ML)
	$(PY) -m pip install -e ".[dev,dashboard]"

install-ml: ## Install Ultralytics / PyTorch for inference and training
	$(PY) -m pip install -e ".[ml]"

lint: ## Lint and check formatting
	ruff check . && ruff format --check .

format: ## Auto-fix and format
	ruff check --fix . && ruff format .

test: ## Unit tests with coverage
	pytest --cov

run: ## Run the API locally
	uvicorn services.api.main:app --reload --port 8000

dashboard: ## Run the dashboard locally
	streamlit run services/dashboard/app.py

data: ## Build the SKU-110K subset (1000 / 200 / 200)
	$(PY) training/scripts/prepare_subset.py --config training/configs/data_subset.yaml

eda: ## Compute EDA statistics for the SKU-110K subset
	$(PY) training/scripts/eda.py --data-dir data/sku110k_subset --out-md docs/reports/sku110k_eda.md --out-json docs/reports/sku110k_eda.json

train: ## Fine-tune the detector (GPU)
	$(PY) training/scripts/train.py --config training/configs/train_yolov8n.yaml

evaluate: ## Evaluate a model version on the test split
	$(PY) training/scripts/evaluate.py --model-version $(MODEL_VERSION)

up: ## Start API + dashboard with Docker Compose
	docker compose up -d --build

down: ## Stop services
	docker compose down

.PHONY: help install install-ml lint format test run dashboard data train evaluate up down
