.PHONY: install lint format test check up down logs

install:
	uv sync

lint:
	uv run ruff check .
	uv run mypy src tests

format:
	uv run ruff format .

test:
	uv run pytest

check: format lint test

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f db

test-cov:
	uv run pytest --cov=src --cov-report=term-missing

test-fast:
	uv run pytest -x -q

db:
	docker compose exec db psql -U agente -d agente_db

reset:
	docker compose down -v
	docker compose up -d