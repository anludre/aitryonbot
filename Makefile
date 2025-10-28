PY=python3

.PHONY: dev lint fmt test hooks worker

# Run FastAPI dev server (webhook endpoint)
dev:
	uvicorn bot.main:app --reload --host 0.0.0.0 --port 8000

# Lint checks
lint:
	ruff check .
	black --check --line-length 100 .
	isort --check-only --line-length 100 --profile black .

# Auto-format
fmt:
	black --line-length 100 .
	isort --line-length 100 --profile black .
	ruff check --fix .

# Tests
test:
	pytest -q

# Install pre-commit hooks
hooks:
	pre-commit install

# Run Celery worker (adjust module once worker is added)
worker:
	celery -A bot.worker worker -Q models,items,tryon -l info
