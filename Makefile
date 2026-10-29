PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
UVICORN := $(VENV)/bin/uvicorn

.PHONY: help install backend-install frontend-install dev backend frontend \
	test test-backend test-frontend lint lint-backend lint-frontend type eval build \
	run docker-up docker-down clean

help:
	@echo "install        Create the virtualenv and install backend + frontend deps"
	@echo "dev            Run the API and Vite dev server together"
	@echo "backend        Run the FastAPI server on :8000"
	@echo "frontend       Run the Vite dev server on :5173"
	@echo "test           Run backend and frontend tests"
	@echo "lint           Run Ruff and ESLint"
	@echo "type           Run Mypy on the backend"
	@echo "eval           Run the offline memory-extraction evaluation"
	@echo "build          Build the production frontend bundle"
	@echo "run            Build the frontend and serve everything on :8000"
	@echo "docker-up      Start the full stack with Docker Compose"
	@echo "docker-down    Stop the Docker Compose stack"

install: backend-install frontend-install

backend-install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements-dev.txt

frontend-install:
	cd frontend && npm ci

dev:
	@echo "API:      http://127.0.0.1:8000"
	@echo "Frontend: http://127.0.0.1:5173"
	@trap 'kill 0' INT TERM; \
		$(UVICORN) backend.app.main:app --reload --port 8000 & \
		cd frontend && npm run dev

backend:
	$(UVICORN) backend.app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	$(PY) -m pytest

test-frontend:
	cd frontend && npm test

lint: lint-backend lint-frontend

lint-backend:
	$(PY) -m ruff check backend
	$(PY) -m ruff format --check backend

lint-frontend:
	cd frontend && npm run lint

type:
	$(VENV)/bin/mypy backend/app

eval:
	$(PY) -m backend.eval.memory_eval --backend fixture

build:
	cd frontend && npm run build

run: build
	$(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov frontend/dist
	find backend -type d -name __pycache__ -prune -exec rm -rf {} +
