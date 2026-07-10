# Единая точка входа (implementation-plan.md §3)
.PHONY: dev dev-backend dev-frontend test lint build e2e docker

dev: ## бэкенд (:8000) и фронтенд (:5173) параллельно
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uv run uvicorn app.main:create_app --factory --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npx tsc -b --noEmit || npx tsc --noEmit

build:
	cd frontend && npm ci && npm run build

e2e: ## требует запущенного приложения на :8000 (docker compose up или make dev-backend после make build)
	cd e2e && npm ci && npx playwright test

docker:
	docker compose up --build
