# ADR-009: multi-stage — node собирает SPA, python-стадия раздаёт её тем же процессом
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/schema.sql ./schema.sql
COPY backend/app ./app
COPY --from=frontend /build/dist ./static

ENV KANBAN_DB_PATH=/data/kanban.db \
    KANBAN_STATIC_DIR=/app/static \
    PATH="/app/.venv/bin:$PATH"
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
