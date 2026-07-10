# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

**MVP implemented.** The spec lives in [docs.md](docs.md) (Russian): product vision, domain model, user stories with AC, SQLite schema, REST API contract, ADRs, UX spec, Definition of Done. The build plan with stack decisions (ADR-004…010) is [implementation-plan.md](implementation-plan.md). Read both before changing domain behavior.

## Commands

```sh
make dev           # backend :8000 (uvicorn --reload) + frontend :5173 (vite, /api proxy)
make test          # backend unit + contract tests (cd backend && uv run pytest)
make lint          # ruff check/format + tsc --noEmit
make build         # frontend build → frontend/dist
make e2e           # Playwright against a running app on :8000 (needs built frontend)
docker compose up --build   # production-style run on :8000
```

Backend: Python 3.12+/FastAPI/stdlib sqlite3, managed by **uv** (run everything via `uv run` from `backend/`). Frontend: Vite + React + TS + TanStack Query + @dnd-kit (`frontend/`). E2E: Playwright (`e2e/`), scenarios in `e2e/tests/scenarios.spec.ts` use the `data-testid` attributes in the frontend — keep them stable.

## Layout (implementation-plan.md §3)

- `backend/app/api/` — thin routers + `errors.py` (exception→HTTP mapping); no domain rules here, ever (ADR-001).
- `backend/app/services/` — ALL domain logic (cycles via DFS, position renumbering, WIP warnings, cascades, `is_final`→`completed_at`, validation). Services take a sqlite3 connection, never know about HTTP.
- `backend/app/repo/` — SQL only; `db.py` holds connection pragmas + `PRAGMA user_version` migrations from `backend/schema.sql`.
- `backend/app/schemas/` — Pydantic request/response models.
- `frontend/src/i18n/ru.ts` — ALL UI strings (ADR-008); never hardcode strings in components.

## What is being built

A lightweight, local-first, API-first personal Kanban tracker: boards → columns → tasks, plus typed directed links between tasks. Single user, no auth beyond an optional static bearer token (`KANBAN_TOKEN`, empty ⇒ auth off). Data lives in a single SQLite file (`KANBAN_DB_PATH`). UI language is Russian (strings externalized for future i18n). One docker-compose service serves API + SPA from the same process.

## Binding architecture decisions (from docs.md §7)

- **ADR-001 — layering is the load-bearing decision:** all domain logic (cycle checks, position recalculation, WIP warnings, cascades, validation) lives in a **service layer**. HTTP API and the future MCP server are equally thin adapters over it. Never put domain rules in route handlers — MCP integration (post-MVP stage 2) depends on this.
- **ADR-002:** SQLite, single file, accessed through a repository layer. No Postgres migration planned.
- **ADR-003:** no WebSockets in MVP. Optimistic UI updates; reload the board on error.
- Positions are plain integers with full renumbering on reorder, inside a transaction (no fractional indexing).
- `tasks.column_id` deliberately has **no** `ON DELETE CASCADE` — column deletion is handled by two explicit API scenarios (move tasks elsewhere via `?move_tasks_to=`, or 409 if tasks exist and no target given).

## Domain rules that must always hold

- Link types: `blocks`, `subtask_of` (cycle-forbidden; `subtask_of` also max one parent), `relates_to` (symmetric), `duplicates`. Cycle detection is done in the service layer (graph DFS/BFS per link type) before insert.
- No self-links; no duplicate `(source, target, type)` pairs; cross-board links are allowed.
- WIP limits are soft: warn, never block.
- The last remaining column of a board cannot be deleted (409).
- Deleting a board cascades to its columns, tasks, and any links touching its tasks; deleting a task cascades to its links.
- All mutations are transactional/atomic.

## API contract (docs.md §6)

REST JSON under `/api/v1`, optional `Authorization: Bearer <token>`. Unified error shape:

```json
{ "error": { "code": "LINK_CYCLE", "message": "..." } }
```

Status codes: 400 validation, 401, 404, 409 state conflict, 422 domain-rule violation (cycles, self-link, duplicate link). `GET /boards/{id}` returns the whole board (columns + tasks) and is the UI's primary query. Moves are atomic single endpoints (`POST /tasks/{id}/move`, `POST /columns/{id}/move`).

## Post-MVP direction (shapes MVP code)

Stage 2 is an MCP server calling the same service layer; stage 3 is calendar integration (iCal feed first). This is why API-first and the service-layer split are non-negotiable in the MVP.

## Open questions (docs.md appendix — ask, don't assume)

Autosave vs explicit save on task cards; whether board/task archiving lands in MVP; whether a "final" column auto-sets `completed_at`; whether cross-board links are exposed in the UI.
