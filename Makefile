# PriceTracker shortcuts. GNU Make is optional.
# Windows: run these targets from WSL/Git Bash, or copy the command printed by
# `make help` into PowerShell. Every underlying command is cross-platform.

COMPOSE := docker compose --env-file .env -f infra/compose.yaml
UV_RUN := uv run --project apps/api
PNPM := pnpm --dir apps/web

.DEFAULT_GOAL := help

.PHONY: help setup env infra-up infra-down deploy-check deploy \
	dev-api dev-worker dev-scheduler dev-web \
	migrate migration lint typecheck test build compose-validate compose-build clean

help:
	@echo "setup             Install frontend and backend dependencies"
	@echo "env               Create .env from .env.example (Python 3 required)"
	@echo "infra-up          Start PostgreSQL, Redis, and Mailpit"
	@echo "deploy-check      Validate .env for a production deploy"
	@echo "deploy            Run scripts/deploy.sh on the VPS (VPS_HOST=user@host)"
	@echo "dev-api           Run the FastAPI development server"
	@echo "dev-worker        Run the Celery worker"
	@echo "dev-scheduler     Run the Celery beat scheduler"
	@echo "dev-web           Run the Next.js development server"
	@echo "migrate           Apply database migrations"
	@echo "migration m=name  Create an Alembic migration"
	@echo "lint/typecheck    Check both applications"
	@echo "test/build        Test both apps / build containers and web"
	@echo ""
	@echo "PowerShell fallback examples:"
	@echo "  Copy-Item .env.example .env"
	@echo "  Copy-Item apps/web/.env.example apps/web/.env.local"
	@echo "  docker compose --env-file .env -f infra/compose.yaml up -d postgres redis mailpit"
	@echo "  uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head"
	@echo "  pnpm --dir apps/web dev"

env:
	python -c "from pathlib import Path; p=Path('.env'); p.exists() or p.write_text(Path('.env.example').read_text())"
	python -c "from pathlib import Path; p=Path('apps/web/.env.local'); p.exists() or p.write_text(Path('apps/web/.env.example').read_text())"

setup:
	corepack enable
	pnpm install
	uv sync --project apps/api --extra dev

infra-up:
	$(COMPOSE) up -d postgres redis mailpit

infra-down:
	$(COMPOSE) down

deploy-check:
	python scripts/check_live_env.py --env-file .env

deploy:
	@test -n "$(VPS_HOST)" || (echo "Usage: make deploy VPS_HOST=user@host [VPS_PATH=/opt/pricetracker]" && exit 1)
	ssh $(VPS_HOST) "cd $(or $(VPS_PATH),/opt/pricetracker) && ./scripts/deploy.sh"

dev-api:
	$(UV_RUN) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	$(UV_RUN) celery -A app.workers.celery_app worker --loglevel=INFO

dev-scheduler:
	$(UV_RUN) celery -A app.workers.celery_app beat --loglevel=INFO

dev-web:
	$(PNPM) dev

migrate:
	$(UV_RUN) alembic -c apps/api/alembic.ini upgrade head

migration:
	@test -n "$(m)" || (echo "Usage: make migration m=describe_change" && exit 1)
	$(UV_RUN) alembic -c apps/api/alembic.ini revision --autogenerate -m "$(m)"

lint:
	$(UV_RUN) --with ruff ruff check apps/api
	$(UV_RUN) --with ruff ruff format --check apps/api
	$(PNPM) lint

typecheck:
	$(UV_RUN) --with mypy mypy --config-file apps/api/pyproject.toml apps/api/app
	$(PNPM) typecheck

test:
	$(UV_RUN) pytest
	$(PNPM) test

build:
	$(PNPM) build
	$(COMPOSE) build api worker scheduler web

compose-validate:
	$(COMPOSE) config --quiet

compose-build:
	$(COMPOSE) build api worker scheduler web

clean:
	$(COMPOSE) down --remove-orphans

