.PHONY: dev-backend dev-frontend dev-up dev-down lint test clean

# === Development ===

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-up:
	docker compose up -d

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

# === Docker ===

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

ps:
	docker compose ps

# === Quality ===

lint:
	cd backend && ruff check . && cd ../frontend && npm run lint

lint-fix:
	cd backend && ruff check --fix . && cd ../frontend && npm run lint -- --fix

typecheck:
	cd backend && pyright . && cd ../frontend && npm run typecheck

# === Test ===

test:
	cd backend && pytest

test-cov:
	cd backend && pytest --cov=app --cov-report=term-missing

# === Clean ===

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist 2>/dev/null || true
