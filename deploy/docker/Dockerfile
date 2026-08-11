# App Shell - run-lane image: API + built UI in one container.
#
# Three stages:
#   ui-build  - Node builds the SPA into ui/dist (SEs never install Node)
#   py-build  - uv resolves the FROZEN lockfile into /app/.venv
#   runtime   - slim Python, non-root, venv + src + dist. No uv, no npm,
#               no compilers. Secrets never enter layers (.dockerignore
#               excludes .env*; keys arrive at runtime via env_file/mount).
#
# Build (from repo root):
#   docker build -f deploy/docker/Dockerfile -t app-shell:dev .

# -- Stage 1: UI ----------------------------------------------------
FROM node:22-alpine AS ui-build
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ui/.npmrc ./
RUN npm ci --no-audit --no-fund
COPY ui/ ./
RUN npm run build

# -- Stage 2: Python deps (frozen) ---------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS py-build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Deps first (cache-friendly): lockfile only, no project code.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
# Then the project itself.
COPY src/ src/
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# -- Stage 3: runtime -----------------------------------------------
FROM python:3.13-slim-bookworm AS runtime
WORKDIR /app

# Non-root user - the API needs no privileges, and the mounted .env is
# owned by the host user anyway.
RUN groupadd -r appshell && useradd -r -g appshell -d /app appshell

COPY --from=py-build /app/.venv /app/.venv
COPY --from=py-build /app/src /app/src
# pyproject marks the project root - setup persistence resolves the
# canonical .env location by walking up to it (mounted at /app/.env).
COPY pyproject.toml /app/pyproject.toml
COPY --from=ui-build /ui/dist /app/ui/dist

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    # Subprocesses (pipeline phases, emitter) use the venv directly -
    # uv does not exist in this image.
    APPSHELL_CLI_PREFIX="python -m" \
    APPSHELL_UI_DIST=/app/ui/dist

EXPOSE 8765
USER appshell

CMD ["uvicorn", "appshell.api.main:app", "--host", "0.0.0.0", "--port", "8765"]
