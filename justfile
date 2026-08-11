# App Shell - dev-loop source of truth. All Python runs via `uv run`.
# Two first-class lanes:
#   run lane:  `just run`          - Docker, zero toolchain, for non-engineers
#   dev lane:  `just api` + `just ui` - hot reload for contributors

set dotenv-load := true

compose := "docker compose -f deploy/docker/compose.yaml"

default:
    @just --list

# === Setup ===

# Install backend + frontend dependencies.
install:
    uv sync
    cd ui && npm install

# Copy .env.example to .env if missing.
env:
    @test -f .env || (cp .env.example .env && echo "created .env - fill in your keys")

# === Run lane (Docker, one port) ===

# Build and start the full stack (Postgres + app) in Docker Desktop.
run: env
    {{compose}} --profile app up --build -d
    @echo "-> http://localhost:8765"

# Stop everything (keeps the Postgres volume).
stop:
    {{compose}} --profile app down

# Tail app logs.
logs:
    {{compose}} logs -f api

# === Dev lane (hot reload) ===

# Start only Postgres.
up:
    {{compose}} up -d postgres

# Stop Postgres.
down:
    {{compose}} down

# API with hot reload on :8765.
api:
    uv run appshell serve --reload

# Vite dev server on :5173 (proxies /api -> :8765).
ui:
    cd ui && npm run dev

# === Database ===

db-init:
    uv run appshell db init

db-reset:
    uv run appshell db reset --yes

db-status:
    uv run appshell db status

# Seed demo data for the example Items + Profiles pages.
seed:
    uv run appshell items seed
    uv run appshell profiles seed
    uv run appshell users seed

# === Quality gates ===

lint:
    uv run ruff check src tests

fmt:
    uv run ruff format src tests
    uv run ruff check --fix src tests

typecheck:
    uv run mypy

test:
    uv run pytest

# Integration tests need Docker (testcontainers Postgres).
test-integration:
    uv run pytest -m integration

# Everything a PR must pass.
check: lint typecheck test

# Build the production UI bundle.
ui-build:
    cd ui && npm run build

# Environment sanity check.
doctor:
    uv run appshell doctor
