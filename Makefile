.PHONY: build up down dev test lint format typecheck clean all help

# Default target
help:
	@echo "Available commands:"
	@echo "  build      - Build Docker images"
	@echo "  up         - Start the full stack with Docker Compose"
	@echo "  down       - Stop the full stack"
	@echo "  dev        - Start the backend in local development mode"
	@echo "  test       - Run all tests with pytest"
	@echo "  lint       - Run Ruff linter"
	@echo "  format     - Run Black formatter and Ruff auto-fix"
	@echo "  typecheck  - Run MyPy type checker"
	@echo "  clean      - Remove build artifacts and cache"
	@echo "  all        - Run format, lint, typecheck, and test"

# Docker
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down -v

# Local development
dev:
	@echo "Starting development server..."
	@cd backend && python -m uvicorn ocr_platform.main:app --host 0.0.0.0 --port 8000 --reload

# Worker
worker:
	@echo "Starting Celery worker..."
	@cd backend && celery -A ocr_platform.jobs.celery_app worker --loglevel=info --concurrency=2

# Scale workers (requires running Redis)
scale-workers:
	@echo "Scaling to 3 workers..."
	@cd backend && for i in 1 2 3; do \
		start /b celery -A ocr_platform.jobs.celery_app worker --loglevel=info --concurrency=2 -n worker%%i; \
	done

# Testing
test:
	cd backend && python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Linting & Formatting
lint:
	cd backend && ruff check src/ tests/

format:
	cd backend && black src/ tests/ && ruff check src/ tests/ --fix

typecheck:
	cd backend && mypy src/ tests/

# CI pipeline
all: format lint typecheck test

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	rm -rf build/ dist/ *.egg-info/
