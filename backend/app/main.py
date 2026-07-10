"""Сборка приложения: логирование, миграции, роутеры, auth, раздача SPA (ADR-009/010).

Запуск: uvicorn app.main:create_app --factory
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import boards, columns, errors, links, tasks
from app.api.deps import require_auth
from app.repo import db

access_log = logging.getLogger("kanban.access")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        data = getattr(record, "data", None)
        if data is not None:
            payload["data"] = data
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.environ.get("KANBAN_LOG_LEVEL", "INFO").upper())


def _static_dir() -> Path | None:
    configured = os.environ.get("KANBAN_STATIC_DIR")
    candidate = (
        Path(configured)
        if configured
        else Path(__file__).resolve().parents[2] / "frontend" / "dist"
    )
    return candidate if candidate.is_dir() else None


def create_app(db_path: str | None = None) -> FastAPI:
    setup_logging()
    db_path = db_path or os.environ.get("KANBAN_DB_PATH", "kanban.db")
    conn = db.connect(db_path)
    db.migrate(conn)
    conn.close()

    app = FastAPI(title="light-kanban", version="0.1.0")
    app.state.db_path = db_path
    errors.register(app)

    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    protected = [Depends(require_auth)]
    for router in (boards.router, columns.router, tasks.router, links.router):
        api.include_router(router, dependencies=protected)
    app.include_router(api)

    @app.middleware("http")
    async def access(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        access_log.info(
            "request",
            extra={
                "data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - start) * 1000, 1),
                }
            },
        )
        return response

    static = _static_dir()
    if static is not None:
        app.mount("/", StaticFiles(directory=static, html=True), name="spa")

    return app
